import pytest
import os
from unittest.mock import patch, MagicMock

from schemas.domain import CircuitGraph, DetectedComponent, WireSegment, Junction, Point, SimulationRequest, BoundingBox, Pin, CircuitNode
from services.detector_service import DetectorService
from services.graph_service import GraphBuilderService
from services.validator_service import CircuitValidator
from services.simulator_service import CircuitSimulator, NgSpiceSimulationError

@pytest.fixture
def sample_components():
    return [
        DetectedComponent(id="V1", type="battery", value="9V", bbox=BoundingBox(x=0, y=0, w=10, h=10), pins=[]),
        DetectedComponent(id="R1", type="resistor", value="1k", bbox=BoundingBox(x=0, y=0, w=10, h=10), pins=[])
    ]

@pytest.mark.asyncio
@patch('services.detector_service.ComponentDetector.detect')
async def test_detector_service_mocked(mock_detect, sample_components):
    """Test DetectorService with mocked underlying ML detector."""
    mock_detect.return_value = (sample_components, [], [])
    
    # We mock the entire ComponentDetector, or just the detector.detect.
    # The detector_service.detect might be calling wire_detector.
    with patch('services.detector_service.load_image_from_bytes') as mock_load:
        mock_load.return_value = MagicMock()
        with patch('services.detector_service.ImagePreprocessor.process') as mock_preprocess:
            mock_preprocess.return_value = MagicMock(binary=MagicMock(), original=MagicMock())
            mock_preprocess.return_value.original.shape = (800, 600, 3)
            with patch('cv2.cvtColor'):
                with patch('PIL.Image.fromarray'):
                    with patch('services.detector_service.WireDetector.detect') as mock_wire_detect:
                        with patch('services.detector_service.LabelDetector.detect_labels') as mock_labels:
                            mock_labels.return_value = []
                            mock_wire_detect.return_value = ([], [])
                            
                            service = DetectorService()
                            
                            components, wires, junctions, labels, w, h = await service.detect_from_image(b"fake_image_bytes")
            
            assert len(components) == 2
            assert components[0].id == "V1"

def test_graph_builder_service():
    """Test GraphBuilderService union-find logic."""
    comps = [
        DetectedComponent(id="V1", type="battery", value="9V", bbox=BoundingBox(x=0, y=0, w=10, h=10), pins=[
            Pin(name="pin1", x=10, y=10), Pin(name="pin2", x=10, y=20)
        ]),
        DetectedComponent(id="R1", type="resistor", value="1k", bbox=BoundingBox(x=0, y=0, w=10, h=10), pins=[
            Pin(name="pin1", x=30, y=10), Pin(name="pin2", x=30, y=20)
        ])
    ]
    wires = [
        WireSegment(id="W1", start=Point(x=10, y=10), end=Point(x=30, y=10)),
        WireSegment(id="W2", start=Point(x=10, y=20), end=Point(x=30, y=20)),
    ]
    
    builder = GraphBuilderService()
    circuit = builder.build_graph(comps, wires, [], [], 1200, 800)
    
    assert len(circuit.nodes) == 2
    assert circuit.nodes[0].connected_pins == ['V1.pin1', 'R1.pin1']

def test_validator_service():
    """Test ValidatorService heuristics."""
    circuit = CircuitGraph(
        components=[
            DetectedComponent(id="V1", type="battery", value="9V", bbox=BoundingBox(x=0, y=0, w=10, h=10), pins=[]),
            DetectedComponent(id="R1", type="resistor", value="1k", bbox=BoundingBox(x=0, y=0, w=10, h=10), pins=[])
        ],
        wires=[], junctions=[], nodes=[], labels=[], image_width=800, image_height=600
    )
    
    validator = CircuitValidator(circuit)
    report = validator.validate()
    
    assert not report.is_valid
    errors = [c for c in report.checks if c.status == 'error']
    assert len(errors) > 0

@patch('PySpice.Spice.Netlist.Circuit.simulator')
def test_simulator_service(mock_simulator):
    """Test SimulatorService with mocked PySpice."""
    circuit = CircuitGraph(
        components=[
            DetectedComponent(id="V1", type="battery", value="9V", bbox=BoundingBox(x=0, y=0, w=10, h=10), pins=[]),
            DetectedComponent(id="R1", type="resistor", value="1k", bbox=BoundingBox(x=0, y=0, w=10, h=10), pins=[]),
            DetectedComponent(id="GND1", type="ground", value="", bbox=BoundingBox(x=0, y=0, w=10, h=10), pins=[])
        ],
        wires=[], junctions=[], 
        nodes=[
            CircuitNode(id="N1", connected_pins=['V1.pin1', 'R1.pin1'], label=""),
            CircuitNode(id="N2", connected_pins=['V1.pin2', 'R1.pin2', 'GND1.pin1'], label="GND")
        ], 
        labels=[], image_width=800, image_height=600
    )
    
    request = SimulationRequest(circuit=circuit, analysis_type="dc")
    
    # Simulator should build without raising exceptions
    sim = CircuitSimulator(request)
    
    # Mock simulation run
    mock_sim_instance = mock_simulator.return_value
    mock_sim_instance.operating_point.return_value.nodes.values.return_value = []
    mock_sim_instance.operating_point.return_value.branches.values.return_value = []
    
    response = sim.run()
    assert response.analysis_type == "dc"
