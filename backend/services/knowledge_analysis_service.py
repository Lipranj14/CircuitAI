from schemas.domain import CircuitGraph
from schemas.knowledge import CircuitKnowledge
from services.knowledge.topology_service import TopologyService
from services.knowledge.flow_service import CurrentDirectionService, CurrentPathService
from services.knowledge.equation_service import EquationService

class KnowledgeAnalysisService:
    """
    Orchestrates the individual knowledge engine services into a single unified analysis.
    """
    def __init__(self, graph: CircuitGraph):
        self.graph = graph

    def run_analysis(self) -> CircuitKnowledge:
        # 1. Topology
        topology = TopologyService(self.graph)
        topology_data = topology.extract_topology()
        grouping_data = topology.extract_groupings()
        
        # 2. Flow and Direction
        dir_service = CurrentDirectionService(topology)
        dg = dir_service.compute_directions()
        
        path_service = CurrentPathService(dg, self.graph, dir_service.polarity)
        flow_data = path_service.compute_flow_data()
        
        # 3. Equations
        eq_service = EquationService(topology, dir_service)
        equations = eq_service.compute_equations()
        
        # Determine circuit type, difficulty, laws, and candidate equations
        comp_types = [c.type.lower() for c in self.graph.components]
        has_cap = "capacitor" in comp_types
        has_ind = "inductor" in comp_types
        has_diode = any(t in comp_types for t in ["diode", "led"])
        
        if has_cap or has_ind:
            circuit_type = "Dynamic RLC Circuit"
        elif has_diode:
            circuit_type = "Diode Circuit"
        else:
            circuit_type = "DC Resistive Circuit"
            
        # Determine difficulty
        if circuit_type == "DC Resistive Circuit" and len(comp_types) <= 3:
            difficulty = "Beginner"
        else:
            difficulty = "Intermediate"
            
        # Laws and candidate equations
        applicable_laws = []
        candidate_equations = []
        if circuit_type == "DC Resistive Circuit":
            applicable_laws = ["Ohm's Law", "KVL", "KCL"]
            candidate_equations = ["V = I * R"]
        else:
            applicable_laws = ["KVL", "KCL"]
            if has_cap:
                applicable_laws.append("Capacitor I-V Relation")
                candidate_equations.append("I = C * dV/dt")
            if has_ind:
                applicable_laws.append("Inductor V-I Relation")
                candidate_equations.append("V = L * dI/dt")
            if has_diode:
                applicable_laws.append("Diode I-V Characteristics")
                candidate_equations.append("I = Is * (e^(Vd/(n*Vt)) - 1)")
                
        component_count = len(self.graph.components)
        node_count = len(topology_data.nodes)
        branch_count = len(topology_data.branches)
        loop_count = len(topology_data.loops)

        # 4. Learning Metadata (Basic mapping for now)
        learning_metadata = {
            "num_nodes": node_count,
            "num_loops": loop_count,
            "num_branches": branch_count,
            "has_series": len(grouping_data.series_groups) > 0,
            "has_parallel": len(grouping_data.parallel_groups) > 0
        }
        
        return CircuitKnowledge(
            topology=topology_data,
            flow=flow_data,
            grouping=grouping_data,
            equations=equations,
            learning_metadata=learning_metadata,
            circuit_type=circuit_type,
            difficulty=difficulty,
            component_count=component_count,
            node_count=node_count,
            branch_count=branch_count,
            loop_count=loop_count,
            applicable_laws=applicable_laws,
            candidate_equations=candidate_equations
        )
