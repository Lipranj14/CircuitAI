import pytest
from services.pipeline_orchestrator import PipelineOrchestrator
from schemas.domain import DetectedComponent
import asyncio

class MockDetector:
    async def detect_from_image(self, image_bytes):
        # Return mock detection data
        components = [
            DetectedComponent(id="V1", type="battery", bbox={"x":0, "y":0, "w":10, "h":10}),
            DetectedComponent(id="R1", type="resistor", bbox={"x":0, "y":0, "w":10, "h":10})
        ]
        wires = []
        junctions = []
        labels = []
        return components, wires, junctions, labels, 800, 600

@pytest.mark.asyncio
async def test_pipeline_orchestrator_flow():
    orchestrator = PipelineOrchestrator()
    # Mock the detector service to avoid external API calls
    orchestrator.detector = MockDetector()
    
    # Run the pipeline
    result = await orchestrator.run_pipeline(b"mock_image_bytes")
    
    # Verify the structure of the output
    assert "circuit" in result
    assert "svg" in result
    assert "analysis" in result
    
    analysis = result["analysis"]
    # Check that knowledge engine data is populated
    assert "topology" in analysis
    assert "flow" in analysis
    assert "grouping" in analysis
    assert "equations" in analysis

if __name__ == "__main__":
    asyncio.run(test_pipeline_orchestrator_flow())
