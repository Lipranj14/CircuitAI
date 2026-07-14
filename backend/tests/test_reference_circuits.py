import pytest
from schemas.domain import CircuitGraph, DetectedComponent, CircuitNode, BoundingBox, Pin
from services.knowledge_analysis_service import KnowledgeAnalysisService

def create_component(id, type, label=""):
    return DetectedComponent(
        id=id, type=type, label=label or id,
        bbox=BoundingBox(x=0,y=0,w=10,h=10),
        pins=[Pin(name="pin1", x=0, y=0), Pin(name="pin2", x=0, y=0)]
    )

def link_pins(graph: CircuitGraph):
    for node in graph.nodes:
        for pin_key in node.connected_pins:
            comp_id, pin_name = pin_key.split(".")
            for comp in graph.components:
                if comp.id == comp_id:
                    for p in comp.pins:
                        if p.name == pin_name:
                            p.connected_node = node.id

def test_series_circuit():
    graph = CircuitGraph(
        components=[
            create_component("V1", "battery"),
            create_component("R1", "resistor"),
            create_component("R2", "resistor")
        ],
        nodes=[
            CircuitNode(id="N1", connected_pins=["V1.pin1", "R1.pin1"]),
            CircuitNode(id="N2", connected_pins=["R1.pin2", "R2.pin1"]),
            CircuitNode(id="0", connected_pins=["R2.pin2", "V1.pin2"], label="GND")
        ]
    )
    link_pins(graph)
    knowledge = KnowledgeAnalysisService(graph).run_analysis()
    
    assert len(knowledge.topology.nodes) == 3
    assert len(knowledge.topology.loops) == 1
    assert len(knowledge.grouping.series_groups) >= 1
    assert "R1" in knowledge.grouping.series_groups[0]
    assert "R2" in knowledge.grouping.series_groups[0]
    
def test_parallel_circuit():
    graph = CircuitGraph(
        components=[
            create_component("V1", "battery"),
            create_component("R1", "resistor"),
            create_component("R2", "resistor")
        ],
        nodes=[
            CircuitNode(id="N1", connected_pins=["V1.pin1", "R1.pin1", "R2.pin1"]),
            CircuitNode(id="0", connected_pins=["V1.pin2", "R1.pin2", "R2.pin2"], label="GND")
        ]
    )
    link_pins(graph)
    knowledge = KnowledgeAnalysisService(graph).run_analysis()
    
    assert len(knowledge.topology.nodes) == 2
    assert len(knowledge.topology.loops) >= 2
    assert len(knowledge.grouping.parallel_groups) >= 1
    assert "R1" in knowledge.grouping.parallel_groups[0]
    assert "R2" in knowledge.grouping.parallel_groups[0]

def test_two_loop_circuit():
    graph = CircuitGraph(
        components=[
            create_component("V1", "battery"),
            create_component("R1", "resistor"),
            create_component("R2", "resistor"),
            create_component("R3", "resistor")
        ],
        nodes=[
            CircuitNode(id="N1", connected_pins=["V1.pin1", "R1.pin1"]),
            CircuitNode(id="N2", connected_pins=["R1.pin2", "R2.pin1", "R3.pin1"]),
            CircuitNode(id="0", connected_pins=["V1.pin2", "R2.pin2", "R3.pin2"], label="GND")
        ]
    )
    link_pins(graph)
    knowledge = KnowledgeAnalysisService(graph).run_analysis()
    
    assert len(knowledge.topology.nodes) == 3
    assert len(knowledge.topology.loops) >= 2
    assert len(knowledge.grouping.parallel_groups) >= 1
    assert set(["R2", "R3"]).issubset(set(knowledge.grouping.parallel_groups[0]))
    kcl_n2 = next((eq for eq in knowledge.equations if eq.type == "KCL" and eq.related_id == "N2"), None)
    assert kcl_n2 is not None

def test_voltage_divider():
    graph = CircuitGraph(
        components=[
            create_component("V1", "battery"),
            create_component("R1", "resistor"),
            create_component("R2", "resistor")
        ],
        nodes=[
            CircuitNode(id="N1", connected_pins=["V1.pin1", "R1.pin1"]),
            CircuitNode(id="N2", connected_pins=["R1.pin2", "R2.pin1"]),
            CircuitNode(id="0", connected_pins=["V1.pin2", "R2.pin2"], label="GND")
        ]
    )
    link_pins(graph)
    knowledge = KnowledgeAnalysisService(graph).run_analysis()
    
    kvl_eqs = [eq for eq in knowledge.equations if eq.type == "KVL"]
    assert len(kvl_eqs) == 1
    kvl = kvl_eqs[0]
    assert "V1" in kvl.ordered_terms or "-V1" in kvl.ordered_terms

def test_rc_circuit():
    graph = CircuitGraph(
        components=[
            create_component("V1", "battery"),
            create_component("R1", "resistor"),
            create_component("C1", "capacitor")
        ],
        nodes=[
            CircuitNode(id="N1", connected_pins=["V1.pin1", "R1.pin1"]),
            CircuitNode(id="N2", connected_pins=["R1.pin2", "C1.pin1"]),
            CircuitNode(id="0", connected_pins=["V1.pin2", "C1.pin2"], label="GND")
        ]
    )
    link_pins(graph)
    knowledge = KnowledgeAnalysisService(graph).run_analysis()
    
    assert len(knowledge.topology.nodes) == 3
    assert len(knowledge.topology.loops) == 1
    assert len(knowledge.grouping.series_groups) >= 1
