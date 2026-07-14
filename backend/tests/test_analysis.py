import pytest
from schemas.domain import CircuitGraph, DetectedComponent, CircuitNode
from services.analysis_service import AnalysisService

def test_deterministic_analysis_resistive():
    graph = CircuitGraph(
        components=[
            DetectedComponent(id="V1", type="battery", value="9V", bbox={"x": 0, "y": 0, "w": 10, "h": 10}),
            DetectedComponent(id="R1", type="resistor", value="1k", bbox={"x": 0, "y": 0, "w": 10, "h": 10}),
            DetectedComponent(id="R2", type="resistor", value="2k", bbox={"x": 0, "y": 0, "w": 10, "h": 10})
        ],
        nodes=[
            CircuitNode(id="N1", connected_pins=["V1.pin1", "R1.pin1"]),
            CircuitNode(id="N2", connected_pins=["R1.pin2", "R2.pin1"]),
            CircuitNode(id="0", connected_pins=["R2.pin2", "V1.pin2"], label="GND")
        ]
    )
    
    service = AnalysisService(graph)
    analysis = service.analyze()
    
    assert analysis.circuit_type == "DC Resistive Circuit"
    assert analysis.component_count == 3
    assert analysis.node_count == 3
    assert analysis.branch_count == 3
    # B - (N - 1) = 3 - 2 = 1
    assert analysis.loop_count == 1
    assert analysis.difficulty == "Beginner"
    assert "Ohm's Law" in analysis.applicable_laws
    assert "V = I * R" in analysis.candidate_equations

def test_deterministic_analysis_rlc():
    graph = CircuitGraph(
        components=[
            DetectedComponent(id="V1", type="battery", bbox={"x": 0, "y": 0, "w": 10, "h": 10}),
            DetectedComponent(id="R1", type="resistor", bbox={"x": 0, "y": 0, "w": 10, "h": 10}),
            DetectedComponent(id="C1", type="capacitor", bbox={"x": 0, "y": 0, "w": 10, "h": 10}),
            DetectedComponent(id="L1", type="inductor", bbox={"x": 0, "y": 0, "w": 10, "h": 10})
        ],
        nodes=[
            CircuitNode(id="1", connected_pins=["V1.pin1", "R1.pin1"]),
            CircuitNode(id="2", connected_pins=["R1.pin2", "C1.pin1"]),
            CircuitNode(id="3", connected_pins=["C1.pin2", "L1.pin1"]),
            CircuitNode(id="0", connected_pins=["L1.pin2", "V1.pin2"], label="GND")
        ]
    )
    
    service = AnalysisService(graph)
    analysis = service.analyze()
    
    assert analysis.circuit_type == "Dynamic RLC Circuit"
    assert analysis.component_count == 4
    assert analysis.branch_count == 4
    assert analysis.node_count == 4
    # 4 - 3 = 1
    assert analysis.loop_count == 1
    assert "Capacitor I-V Relation" in analysis.applicable_laws
    assert "Inductor V-I Relation" in analysis.applicable_laws
