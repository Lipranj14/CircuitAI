from fastapi import APIRouter, File, UploadFile, Request
import traceback
import uuid

from schemas.api import APIResponse
from schemas.domain import CircuitGraph, ValidationReport, SimulationRequest, SimulationResponse
from services.validator_service import CircuitValidator
from pydantic import BaseModel
from services.validator_service import CircuitValidator
from services.simulator_service import CircuitSimulator
from services.pipeline_orchestrator import PipelineOrchestrator

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

class NetlistRequest(BaseModel):
    netlist: str
    debug: bool = False

@router.post("/analyze", response_model=APIResponse)
async def analyze_circuit(request: Request, file: UploadFile = File(...), debug: bool = False):
    req_id = str(uuid.uuid4())
    try:
        image_bytes = await file.read()
        
        orchestrator = PipelineOrchestrator()
        payload = await orchestrator.run_pipeline(image_bytes, debug)

        return APIResponse(
            success=True,
            stage="analyze",
            message="Circuit analyzed successfully",
            data=payload,
            request_id=req_id
        )
        
    except Exception as e:
        # Handled by global exception handler, but we can also raise custom errors
        raise

@router.post("/analyze-netlist", response_model=APIResponse)
async def analyze_netlist(request: NetlistRequest):
    req_id = str(uuid.uuid4())
    try:
        orchestrator = PipelineOrchestrator()
        payload = await orchestrator.run_pipeline_from_netlist(request.netlist, request.debug)

        return APIResponse(
            success=True,
            stage="analyze",
            message="Netlist analyzed successfully",
            data=payload,
            request_id=req_id
        )
        
    except Exception as e:
        raise

@router.post("/validate", response_model=APIResponse[ValidationReport])
async def validate_circuit(circuit: CircuitGraph):
    req_id = str(uuid.uuid4())
    validator = CircuitValidator(circuit)
    report = validator.validate()
    return APIResponse(
        success=True,
        stage="validate",
        message="Circuit validated successfully",
        data=report,
        request_id=req_id
    )

@router.post("/simulate", response_model=APIResponse[SimulationResponse])
async def simulate_circuit(request: SimulationRequest):
    req_id = str(uuid.uuid4())
    simulator = CircuitSimulator(request)
    response = simulator.run()
    return APIResponse(
        success=True,
        stage="simulate",
        message="Simulation completed successfully",
        data=response,
        request_id=req_id
    )
