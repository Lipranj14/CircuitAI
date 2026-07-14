"""
main.py — FastAPI Backend for AI Circuit Learning Platform

Endpoints:
  GET  /                              → Health check
  POST /api/v1/pipeline/analyze       → Full pipeline: preprocess + detect + OCR + wires + graph + SVG
  POST /api/v1/pipeline/validate      → Validation
  POST /api/v1/pipeline/simulate      → SPICE simulation
  POST /api/v1/tutor/chat             → Circuit Tutor Chat
"""

import os
import logging

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================
# App Initialization
# ============================================================

app = FastAPI(
    title="AI Circuit Learning Platform — API",
    description="Upload circuit diagrams, detect components, and reconstruct schematics",
    version="2.0.0",
)

# Exception Handler
from fastapi.responses import JSONResponse
from schemas.api import APIResponse
from core.exceptions import CircuitException
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    stage = "unknown"
    if isinstance(exc, CircuitException) and hasattr(exc, "stage"):
        stage = exc.stage
        
    # Get request ID if available
    req_id = getattr(request.state, "request_id", None)

    logger.error(f"Global Error: {exc}\n{traceback.format_exc()}")
    response = APIResponse(
        success=False,
        stage=stage,
        message="An unexpected error occurred",
        error=str(exc),
        request_id=req_id
    )
    return JSONResponse(
        status_code=500, 
        content=response.model_dump(),
        headers={"Access-Control-Allow-Origin": "*"}
    )

from api.v1.routers import pipeline, tutor, analysis
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(tutor.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")

# Configure CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini API is initialized inside component_detector.py using the new google-genai SDK
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in environment variables. Vision will fail.")


# ============================================================
# Health Check
# ============================================================

@app.get("/", response_model=APIResponse)
def read_root():
    return APIResponse(
        success=True,
        stage="health",
        message="AI Circuit Learning Platform API is running",
        data={"version": "2.0.0"}
    )

@app.get("/api/debug/last-parse")
def get_last_parse():
    from circuit_vision.debug_store import get_last_parse_result
    return get_last_parse_result()





# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
