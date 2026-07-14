import pytest
from schemas.domain import CircuitGraph, DetectedComponent, CircuitNode, WireSegment, Point, BoundingBox, Pin
from services.knowledge.topology_service import TopologyService

def test_topology_series():
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
    
    # Assign connected_nodes directly in pins so _build_graph works
    graph.components[0].pins[0].connected_node = "N1"
    graph.components[0].pins[1].connected_node = "0"
    graph.components[1].pins[0].connected_node = "N1"
    graph.components[1].pins[1].connected_node = "N2"
    graph.components[2].pins[0].connected_node = "N2"
    graph.components[2].pins[1].connected_node = "0"
    
    service = TopologyService(graph)
    topology = service.extract_topology()
    grouping = service.extract_groupings()
    
    # Verify nodes
    assert len(topology.nodes) == 3
    # Verify branches
    assert len(topology.branches) == 3
    
    # Check loops: There should be 1 loop containing V1, R1, R2
    assert len(topology.loops) == 1
    assert set(topology.loops[0].components) == {"V1", "R1", "R2"}
    
    # Verify series: R1 and R2 are in series, V1 is in series with them
    # Because all components are in a single loop, they are all in series.
    assert len(grouping.series_groups) == 1
    assert set(grouping.series_groups[0]) == {"V1", "R1", "R2"}
    assert len(grouping.parallel_groups) == 0

def test_topology_parallel():
    # Parallel circuit: V1 || R1 || R2
    graph = CircuitGraph(
        components=[
            DetectedComponent(id="V1", type="battery", bbox=BoundingBox(x=0,y=0,w=1,h=1), pins=[Pin(name="pin1", x=0, y=0), Pin(name="pin2", x=0, y=0)]),
            DetectedComponent(id="R1", type="resistor", bbox=BoundingBox(x=0,y=0,w=1,h=1), pins=[Pin(name="pin1", x=0, y=0), Pin(name="pin2", x=0, y=0)]),
            DetectedComponent(id="R2", type="resistor", bbox=BoundingBox(x=0,y=0,w=1,h=1), pins=[Pin(name="pin1", x=0, y=0), Pin(name="pin2", x=0, y=0)])
        ],
        nodes=[
            CircuitNode(id="N1", connected_pins=["V1.pin1", "R1.pin1", "R2.pin1"]),
            CircuitNode(id="0", connected_pins=["R2.pin2", "R1.pin2", "V1.pin2"], label="GND")
        ]
    )
    
    graph.components[0].pins[0].connected_node = "N1"
    graph.components[0].pins[1].connected_node = "0"
    graph.components[1].pins[0].connected_node = "N1"
    graph.components[1].pins[1].connected_node = "0"
    graph.components[2].pins[0].connected_node = "N1"
    graph.components[2].pins[1].connected_node = "0"
    
    service = TopologyService(graph)
    topology = service.extract_topology()
    grouping = service.extract_groupings()
    
    # 2 nodes, 3 branches
    assert len(topology.nodes) == 2
    assert len(topology.branches) == 3
    
    # Verify parallel
    assert len(grouping.parallel_groups) == 1
    assert set(grouping.parallel_groups[0]) == {"V1", "R1", "R2"}
    assert len(grouping.series_groups) == 0
    
    # Loops: V1-R1, R1-R2, V1-R2 (3 loops)
    assert len(topology.loops) >= 2
