from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    """Unified API response schema for all endpoints."""
    success: bool = Field(description="Whether the request succeeded")
    stage: str = Field(description="The pipeline stage (e.g., upload, detect, simulate)")
    message: str = Field(description="Human-readable status message")
    data: Optional[T] = Field(default=None, description="The payload of the response")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    request_id: Optional[str] = Field(default=None, description="Trace ID for the request")
