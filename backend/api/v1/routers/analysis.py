from fastapi import APIRouter, HTTPException
from schemas.api import APIResponse
from schemas.domain import CircuitGraph
from schemas.knowledge import CircuitKnowledge
from services.knowledge_analysis_service import KnowledgeAnalysisService
import uuid

router = APIRouter(prefix="/analysis", tags=["Knowledge Engine"])

@router.post("", response_model=APIResponse[CircuitKnowledge])
async def get_circuit_knowledge(graph: CircuitGraph):
    """
    Computes deterministic Circuit Knowledge (Topology, Flow, Groupings, Equations) 
    from the reconstructed CircuitGraph.
    """
    req_id = str(uuid.uuid4())
    try:
        service = KnowledgeAnalysisService(graph)
        knowledge = service.run_analysis()
        
        return APIResponse(
            success=True,
            stage="knowledge_engine",
            message="Deterministic circuit knowledge computed successfully",
            data=knowledge,
            request_id=req_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
