from schemas.domain import CircuitGraph, CircuitAnalysis
from services.knowledge_analysis_service import KnowledgeAnalysisService

class AnalysisService:
    """Compatibility service for deterministic circuit analysis."""
    
    def __init__(self, graph: CircuitGraph):
        self.graph = graph
        self.knowledge_service = KnowledgeAnalysisService(graph)

    def analyze(self) -> CircuitAnalysis:
        knowledge = self.knowledge_service.run_analysis()
        return CircuitAnalysis(
            circuit_type=knowledge.circuit_type,
            difficulty=knowledge.difficulty,
            component_count=knowledge.component_count,
            node_count=knowledge.node_count,
            branch_count=knowledge.branch_count,
            loop_count=knowledge.loop_count,
            applicable_laws=knowledge.applicable_laws,
            candidate_equations=knowledge.candidate_equations
        )
