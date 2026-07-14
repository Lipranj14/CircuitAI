import uuid
from fastapi import APIRouter
from schemas.api import APIResponse
from schemas.domain import TutorRequest, TutorResponse, ComponentMetadataRequest, ComponentEducationalDetails, SuggestedQuestionsRequest, SuggestedQuestionsResponse
from services.tutor_service import CircuitTutor

router = APIRouter(prefix="/tutor", tags=["Tutor"])

@router.post("/chat", response_model=APIResponse[TutorResponse])
async def tutor_chat(request: TutorRequest):
    req_id = str(uuid.uuid4())
    tutor = CircuitTutor(request)
    response = await tutor.generate_response()
    return APIResponse(
        success=True,
        stage="tutor",
        message="Tutor response generated successfully",
        data=response,
        request_id=req_id
    )

@router.post("/component-metadata", response_model=APIResponse[ComponentEducationalDetails])
async def get_component_metadata(request: ComponentMetadataRequest):
    req_id = str(uuid.uuid4())
    # We can instantiate CircuitTutor with a dummy request just to use its methods
    # since these methods only use self.model.
    # A cleaner refactor would make these methods static or take the model directly,
    # but for now, we'll initialize with a dummy request.
    from schemas.domain import CircuitGraph
    dummy_req = TutorRequest(query="", chat_history=[], expertise_level="beginner", circuit=CircuitGraph())
    tutor = CircuitTutor(dummy_req)
    
    response = await tutor.get_component_metadata(request.comp_id, request.comp_type, request.analysis)
    return APIResponse(
        success=True,
        stage="tutor",
        message="Metadata generated",
        data=response,
        request_id=req_id
    )

@router.post("/suggested-questions", response_model=APIResponse[SuggestedQuestionsResponse])
async def generate_suggested_questions(request: SuggestedQuestionsRequest):
    req_id = str(uuid.uuid4())
    from schemas.domain import CircuitGraph
    dummy_req = TutorRequest(query="", chat_history=[], expertise_level="beginner", circuit=CircuitGraph())
    tutor = CircuitTutor(dummy_req)
    
    response = await tutor.generate_suggested_questions(request.analysis)
    return APIResponse(
        success=True,
        stage="tutor",
        message="Questions generated",
        data=response,
        request_id=req_id
    )
