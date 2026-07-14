import networkx as nx
from typing import Dict, List, Tuple
from schemas.domain import CircuitGraph
from schemas.knowledge import TopologyData, GroupingData

class TopologyService:
    """
    Responsible for generating the underlying mathematical graph topology
    from a CircuitGraph. Pure graph traversal without electrical reasoning.
    """
    
    def __init__(self, graph: CircuitGraph):
        self.circuit = graph
        self.G = nx.MultiGraph()
        self._build_graph()

    def _build_graph(self):
        """Build a NetworkX MultiGraph from the CircuitGraph."""
        # Add nodes
        for node in self.circuit.nodes:
            self.G.add_node(node.id, pins=node.connected_pins, label=node.label)
            
        # Map component ID to the set of nodes it connects to
        comp_to_nodes = {}
        for node in self.circuit.nodes:
            for pin_ref in node.connected_pins:
                if "." in pin_ref:
                    comp_id, _ = pin_ref.split(".", 1)
                    if comp_id not in comp_to_nodes:
                        comp_to_nodes[comp_id] = set()
                    comp_to_nodes[comp_id].add(node.id)

        # Add edges (components)
        for comp in self.circuit.components:
            connected_nodes = list(comp_to_nodes.get(comp.id, set()))
            
            # For 2-terminal components (most common)
            if len(connected_nodes) == 2:
                u, v = connected_nodes
                self.G.add_edge(u, v, key=comp.id, component_id=comp.id, type=comp.type)
            elif len(connected_nodes) > 2:
                # Multi-terminal component (e.g. transistor). 
                # Model as a star graph to a central dummy node for topological connectivity.
                dummy_node = f"dummy_{comp.id}"
                self.G.add_node(dummy_node)
                for n in connected_nodes:
                    self.G.add_edge(dummy_node, n, key=comp.id, component_id=comp.id, type=comp.type)

    def extract_topology(self) -> TopologyData:
        """Extract nodes, branches, and fundamental loops."""
        nodes = []
        for n, data in self.G.nodes(data=True):
            if not str(n).startswith("dummy_"):
                nodes.append({"id": n, "pins": data.get("pins", []), "label": data.get("label")})
                
        branches = []
        for u, v, k, data in self.G.edges(data=True, keys=True):
            branches.append({
                "id": data.get("component_id"),
                "node_1": u,
                "node_2": v,
                "type": data.get("type")
            })
            
        # Fundamental loops
        try:
            cycle_basis = nx.cycle_basis(nx.Graph(self.G)) # cycle_basis needs simple graph
            loops = []
            for cycle in cycle_basis:
                # cycle is a list of node IDs. We need the components that form the cycle.
                loop_comps = []
                for i in range(len(cycle)):
                    u = cycle[i]
                    v = cycle[(i + 1) % len(cycle)]
                    # Find edge connecting u and v
                    edge_data = self.G.get_edge_data(u, v)
                    if edge_data:
                        # take the first key (parallel components will form a loop of length 2 separately handled below)
                        first_key = list(edge_data.keys())[0]
                        comp_id = edge_data[first_key].get("component_id")
                        if comp_id and comp_id not in loop_comps:
                            loop_comps.append(comp_id)
                loops.append(loop_comps)
        except Exception as e:
            print(f"DEBUG: cycle_basis exception: {e}")
            loops = []
            
        # Also need loops of length 2 (parallel components)
        for u, v in self.G.edges():
            edge_data = self.G.get_edge_data(u, v)
            if edge_data and len(edge_data) > 1:
                # Parallel components
                comp_ids = [d.get("component_id") for d in edge_data.values()]
                # Generate pairs
                for i in range(len(comp_ids)):
                    for j in range(i+1, len(comp_ids)):
                        loops.append([comp_ids[i], comp_ids[j]])

        # Remove duplicates and format as TopologyLoop
        unique_loops = []
        formatted_loops = []
        loop_counter = 1
        for loop in loops:
            sorted_loop = sorted(loop)
            if sorted_loop not in [sorted(l) for l in unique_loops]:
                unique_loops.append(loop)
                formatted_loops.append({"id": f"Loop_{loop_counter}", "components": loop})
                loop_counter += 1

        return TopologyData(nodes=nodes, branches=branches, loops=formatted_loops)

    def extract_groupings(self) -> GroupingData:
        """Extract series and parallel component groups."""
        series_groups = []
        parallel_groups = []
        
        # Parallel: Multiple edges between the same two nodes
        for u, v in self.G.edges():
            edge_data = self.G.get_edge_data(u, v)
            if edge_data and len(edge_data) > 1:
                comp_ids = [d.get("component_id") for d in edge_data.values()]
                sorted_comps = sorted(comp_ids)
                if sorted_comps not in parallel_groups:
                    parallel_groups.append(sorted_comps)
                    
        # Series: Nodes with degree 2 (exactly two components connected, and they are not dummy)
        visited_nodes = set()
        for n in self.G.nodes():
            if n in visited_nodes or str(n).startswith("dummy_"):
                continue
                
            degree = self.G.degree(n)
            if degree == 2:
                # Possible series connection. Let's trace the full series path.
                path = []
                curr = n
                edges = list(self.G.edges(curr, keys=True, data=True))
                # ... this can get complex to build the maximal path, 
                # for now let's just group the 2 components at this node.
                comp1 = edges[0][3].get("component_id")
                comp2 = edges[1][3].get("component_id")
                if comp1 and comp2:
                    series_groups.append(sorted([comp1, comp2]))
                    
        # Merge series pairs that share components (e.g. [R1, R2] and [R2, R3] -> [R1, R2, R3])
        # Simple disjoint set logic
        merged_series = []
        if series_groups:
            sets = [set(g) for g in series_groups]
            merged = True
            while merged:
                merged = False
                for i in range(len(sets)):
                    for j in range(i+1, len(sets)):
                        if sets[i] & sets[j]:
                            sets[i] = sets[i] | sets[j]
                            sets.pop(j)
                            merged = True
                            break
                    if merged: break
            merged_series = [sorted(list(s)) for s in sets]

        return GroupingData(series_groups=merged_series, parallel_groups=parallel_groups)
