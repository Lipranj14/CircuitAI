import pytest
from schemas.domain import CircuitGraph, DetectedComponent, CircuitNode, BoundingBox, Pin
from services.knowledge.topology_service import TopologyService
from services.knowledge.flow_service import CurrentDirectionService, CurrentPathService

def test_flow_series():
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
    dg = dir_service.compute_directions()
    
    path_service = CurrentPathService(dg, graph, dir_service.polarity)
    flow_data = path_service.compute_flow_data()
    
    # Verify polarity
    assert "V1" in flow_data.polarity
    assert "R1" in flow_data.polarity
    assert "R2" in flow_data.polarity
    
    # Verify current path
    # Path from source (N1) to GND (0): N1 -> N2 -> 0 -> R1, R2
    # The source V1 connects 0 and N1, but we BFS from N1.
    assert len(flow_data.current_paths) == 1
    assert flow_data.current_paths[0] == ["R1", "R2"]
    
    # Verify upstream / downstream
    # R1 is upstream of R2
    assert "R2" in flow_data.downstream.get("R1", [])
    assert "R1" in flow_data.upstream.get("R2", [])
