import networkx as nx
from typing import Dict, List, Set
from schemas.domain import CircuitGraph
from services.knowledge.topology_service import TopologyService
from schemas.knowledge import FlowData

class CurrentDirectionService:
    """
    Computes conventional current flow direction using BFS from sources to ground.
    This establishes the "assumed" polarity for KCL/KVL.
    """
    def __init__(self, topology: TopologyService):
        self.G = topology.G
        self.circuit = topology.circuit
        self.directed_G = nx.MultiDiGraph()
        self.polarity: Dict[str, str] = {} # comp_id -> "u->v"

    def compute_directions(self) -> nx.MultiDiGraph:
        # Identify ground node
        gnd_nodes = [n for n, d in self.G.nodes(data=True) if d.get("label") == "GND" or n == "0"]
        gnd_node = gnd_nodes[0] if gnd_nodes else None

        # Identify source nodes (assume pin1 is positive for simplicity, or look at component type)
        source_nodes = []
        for comp in self.circuit.components:
            if comp.type in ["battery", "voltage_source", "dc_source"]:
                # pin1 is typically positive terminal in our basic representation
                for pin in comp.pins:
                    if pin.name == "pin1" and pin.connected_node:
                        source_nodes.append(pin.connected_node)

        # Build directed graph
        self.directed_G.add_nodes_from(self.G.nodes(data=True))
        
        visited_edges = set()
        
        # Pre-assign sources (assume current flows from GND/negative to positive INSIDE the source)
        for comp in self.circuit.components:
            if comp.type in ["battery", "voltage_source", "dc_source"]:
                pos_node = None
                neg_node = None
                for pin in comp.pins:
                    if pin.name == "pin1": pos_node = pin.connected_node
                    elif pin.name == "pin2": neg_node = pin.connected_node
                
                if pos_node and neg_node:
                    edge_keys = self.G[neg_node].get(pos_node, {})
                    for k, edge_data in edge_keys.items():
                        if edge_data.get("component_id") == comp.id:
                            edge_id = (neg_node, pos_node, k)
                            rev_edge_id = (pos_node, neg_node, k)
                            if edge_id not in visited_edges and rev_edge_id not in visited_edges:
                                self.directed_G.add_edge(neg_node, pos_node, **edge_data)
                                visited_edges.add(edge_id)
                                self.polarity[comp.id] = f"{neg_node}->{pos_node}"

        # BFS from sources
        queue = source_nodes[:]
        visited_nodes = set(source_nodes)
        
        while queue:
            curr = queue.pop(0)
            for neighbor in self.G.neighbors(curr):
                # get all edges between curr and neighbor
                edge_keys = self.G[curr][neighbor]
                for k, edge_data in edge_keys.items():
                    edge_id = (curr, neighbor, k)
                    rev_edge_id = (neighbor, curr, k)
                    
                    if edge_id not in visited_edges and rev_edge_id not in visited_edges:
                        # Direct from curr to neighbor
                        self.directed_G.add_edge(curr, neighbor, **edge_data)
                        visited_edges.add(edge_id)
                        
                        comp_id = edge_data.get("component_id")
                        if comp_id:
                            self.polarity[comp_id] = f"{curr}->{neighbor}"
                            
                if neighbor not in visited_nodes:
                    visited_nodes.add(neighbor)
                    if neighbor != gnd_node:
                        queue.append(neighbor)
                        
        # Handle disconnected or floating components not reached by BFS
        for u, v, k, d in self.G.edges(keys=True, data=True):
            edge_id = (u, v, k)
            rev_edge_id = (v, u, k)
            if edge_id not in visited_edges and rev_edge_id not in visited_edges:
                self.directed_G.add_edge(u, v, **d)
                visited_edges.add(edge_id)
                comp_id = d.get("component_id")
                if comp_id:
                    self.polarity[comp_id] = f"{u}->{v}"

        return self.directed_G


class CurrentPathService:
    """
    Identifies full paths from sources to ground and computes
    upstream/downstream relationships based on the directed graph.
    """
    def __init__(self, directed_G: nx.MultiDiGraph, circuit: CircuitGraph, polarity: Dict[str, str]):
        self.DG = directed_G
        self.circuit = circuit
        self.polarity = polarity

    def compute_flow_data(self) -> FlowData:
        gnd_nodes = [n for n, d in self.DG.nodes(data=True) if d.get("label") == "GND" or n == "0"]
        gnd_node = gnd_nodes[0] if gnd_nodes else None

        source_nodes = []
        for comp in self.circuit.components:
            if comp.type in ["battery", "voltage_source", "dc_source"]:
                for pin in comp.pins:
                    if pin.name == "pin1" and pin.connected_node:
                        source_nodes.append(pin.connected_node)

        current_paths = []
        if gnd_node:
            for src in source_nodes:
                try:
                    # all_simple_paths in MultiDiGraph returns list of nodes. 
                    # We need the components along the path.
                    paths = nx.all_simple_paths(self.DG, src, gnd_node)
                    for path in paths:
                        path_comps = []
                        for i in range(len(path)-1):
                            u = path[i]
                            v = path[i+1]
                            edge_data = self.DG.get_edge_data(u, v)
                            if edge_data:
                                # just take the first key for paths
                                k = list(edge_data.keys())[0]
                                comp_id = edge_data[k].get("component_id")
                                if comp_id:
                                    path_comps.append(comp_id)
                        if path_comps:
                            current_paths.append(path_comps)
                except nx.NetworkXNoPath:
                    pass
        
        # Upstream / Downstream (Transitive closure)
        # If there is a directed path from node A to node B, then edges leaving A are upstream of edges entering B.
        # To simplify, we can do this on a component level.
        # Create a DAG of components.
        comp_dag = nx.DiGraph()
        for u, v, d in self.DG.edges(data=True):
            comp_id = d.get("component_id")
            if comp_id:
                comp_dag.add_node(comp_id)
        
        for n in self.DG.nodes():
            in_edges = self.DG.in_edges(n, data=True)
            out_edges = self.DG.out_edges(n, data=True)
            for _, _, in_d in in_edges:
                for _, _, out_d in out_edges:
                    in_comp = in_d.get("component_id")
                    out_comp = out_d.get("component_id")
                    if in_comp and out_comp and in_comp != out_comp:
                        comp_dag.add_edge(in_comp, out_comp)
                        
        # transitive closure to find all upstream/downstream
        tc = nx.transitive_closure(comp_dag)
        
        upstream = {}
        downstream = {}
        for comp in comp_dag.nodes():
            # downstream: all nodes reachable from comp
            ds = list(tc.successors(comp))
            if ds: downstream[comp] = ds
            
            # upstream: all nodes that can reach comp
            us = list(tc.predecessors(comp))
            if us: upstream[comp] = us

        return FlowData(
            current_paths=current_paths,
            upstream=upstream,
            downstream=downstream,
            polarity=self.polarity
        )
