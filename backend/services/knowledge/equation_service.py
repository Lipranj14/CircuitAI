import networkx as nx
from typing import List, Dict
from schemas.knowledge import StructuredEquation
from services.knowledge.topology_service import TopologyService
from services.knowledge.flow_service import CurrentDirectionService

class EquationService:
    """
    Formulates structured KCL and KVL equations based on topology and flow data.
    """
    def __init__(self, topology: TopologyService, flow: CurrentDirectionService):
        self.topology = topology
        self.flow = flow
        self.G = topology.G
        self.DG = flow.directed_G

    def compute_equations(self) -> List[StructuredEquation]:
        equations = []
        eq_counter = 1

        # KCL Equations
        for n, data in self.G.nodes(data=True):
            if str(n).startswith("dummy_") or data.get("label") == "GND" or n == "0":
                continue
                
            in_edges = self.DG.in_edges(n, data=True)
            out_edges = self.DG.out_edges(n, data=True)
            
            # Sum of currents leaving = 0
            # Outgoing is positive, incoming is negative
            terms = []
            comps = []
            
            for u, v, d in out_edges:
                comp_id = d.get("component_id")
                if comp_id:
                    terms.append(f"I_{comp_id}")
                    comps.append(comp_id)
            
            for u, v, d in in_edges:
                comp_id = d.get("component_id")
                if comp_id:
                    terms.append(f"-I_{comp_id}")
                    comps.append(comp_id)
                    
            if terms:
                equations.append(StructuredEquation(
                    id=f"EQ_{eq_counter}",
                    type="KCL",
                    related_id=n,
                    ordered_terms=terms,
                    participating_components=comps,
                    rendered_string=" + ".join(terms).replace("+ -", "- ") + " = 0"
                ))
                eq_counter += 1

        # KVL Equations
        cycle_basis = []
        try:
            cycle_basis = nx.cycle_basis(nx.Graph(self.G))
        except Exception:
            pass

        for i, cycle in enumerate(cycle_basis):
            terms = []
            comps = []
            
            # Trace the cycle to get voltage drops
            for j in range(len(cycle)):
                u = cycle[j]
                v = cycle[(j + 1) % len(cycle)]
                
                # Check directed edge to determine polarity in loop
                edge_data = self.G.get_edge_data(u, v)
                if not edge_data: continue
                
                k = list(edge_data.keys())[0]
                d = edge_data[k]
                comp_id = d.get("component_id")
                if not comp_id: continue
                
                comps.append(comp_id)
                comp_type = d.get("type", "")
                
                # Check actual flow direction
                flow_dir = self.flow.polarity.get(comp_id)
                # If cycle traverses u->v and flow is u->v, it's a drop in direction of current
                is_with_current = (flow_dir == f"{u}->{v}")
                
                if comp_type in ["battery", "voltage_source", "dc_source"]:
                    # Traveling with current in a source (from - to + inside source): Voltage GAIN
                    if is_with_current:
                        terms.append(f"{comp_id}")
                    else:
                        terms.append(f"-{comp_id}")
                else:
                    # Traveling with current through passive: Voltage DROP
                    if is_with_current:
                        terms.append(f"-I_{comp_id}*{comp_id}")
                    else:
                        terms.append(f"I_{comp_id}*{comp_id}")
            
            if terms:
                # Standardize leading term (make it positive if possible)
                if terms[0].startswith("-"):
                    flipped_terms = []
                    for t in terms:
                        if t.startswith("-"): flipped_terms.append(t[1:])
                        else: flipped_terms.append(f"-{t}")
                    terms = flipped_terms
                
                equations.append(StructuredEquation(
                    id=f"EQ_{eq_counter}",
                    type="KVL",
                    related_id=f"Loop_{i+1}",
                    ordered_terms=terms,
                    participating_components=comps,
                    rendered_string=" + ".join(terms).replace("+ -", "- ") + " = 0"
                ))
                eq_counter += 1

        return equations
