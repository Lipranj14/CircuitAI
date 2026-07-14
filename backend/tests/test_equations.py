import pytest
from schemas.domain import CircuitGraph, DetectedComponent, CircuitNode, BoundingBox, Pin
from services.knowledge.topology_service import TopologyService
from services.knowledge.flow_service import CurrentDirectionService
from services.knowledge.equation_service import EquationService

def test_equation_generation():
    # Simple series circuit: V1 -> R1 -> R2 -> V1
    graph = CircuitGraph(
        components=[
            DetectedComponent(id="V1", type="battery", bbox=BoundingBox(x=0,y=0,w=1,h=1), pins=[Pin(name="pin1", x=0, y=0), Pin(name="pin2", x=0, y=0)]),
            DetectedComponent(id="R1", type="resistor", bbox=BoundingBox(x=0,y=0,w=1,h=1), pins=[Pin(name="pin1", x=0, y=0), Pin(name="pin2", x=0, y=0)]),
            DetectedComponent(id="R2", type="resistor", bbox=BoundingBox(x=0,y=0,w=1,h=1), pins=[Pin(name="pin1", x=0, y=0), Pin(name="pin2", x=0, y=0)])
        ],
        nodes=[
            CircuitNode(id="N1", connected_pins=["V1.pin1", "R1.pin1"]),
            CircuitNode(id="N2", connected_pins=["R1.pin2", "R2.pin1"]),
            CircuitNode(id="0", connected_pins=["R2.pin2", "V1.pin2"], label="GND")
        ]
    )
    
    graph.components[0].pins[0].connected_node = "N1"
    graph.components[0].pins[1].connected_node = "0"
    graph.components[1].pins[0].connected_node = "N1"
    graph.components[1].pins[1].connected_node = "N2"
    graph.components[2].pins[0].connected_node = "N2"
    graph.components[2].pins[1].connected_node = "0"
    
    topology = TopologyService(graph)
    dir_service = CurrentDirectionService(topology)
    dir_service.compute_directions()
    
    eq_service = EquationService(topology, dir_service)
    equations = eq_service.compute_equations()
    
    # Check KCL: nodes N1 and N2
    kcl_eqs = [eq for eq in equations if eq.type == "KCL"]
    assert len(kcl_eqs) == 2
    
    # N1: I_R1 - I_V1 = 0
    # N2: I_R2 - I_R1 = 0
    
    # Check KVL: 1 loop
    kvl_eqs = [eq for eq in equations if eq.type == "KVL"]
    assert len(kvl_eqs) == 1
    
    # The KVL string should contain V1, R1, R2. Something like: V1 - I_R1*R1 - I_R2*R2 = 0
    kvl = kvl_eqs[0].rendered_string
    assert "V1" in kvl
    assert "I_R1*R1" in kvl
    assert "I_R2*R2" in kvl
    assert " = 0" in kvl
