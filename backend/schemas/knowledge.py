from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from schemas.domain import CircuitAnalysis

class StructuredEquation(BaseModel):
    id: str = Field(description="Unique identifier for the equation")
    type: str = Field(description="Type of equation: 'KVL', 'KCL', 'OHMS_LAW', etc.")
    related_id: str = Field(description="ID of the related loop or node")
    ordered_terms: List[str] = Field(description="Terms of the equation in order, e.g. ['V1', '-I_R1*R1']")
    participating_components: List[str] = Field(description="IDs of components involved")
    rendered_string: str = Field(description="Full string representation, e.g. 'V1 - I_R1*R1 = 0'")

class GroupingData(BaseModel):
    series_groups: List[List[str]] = Field(default_factory=list, description="Lists of component IDs in series")
    parallel_groups: List[List[str]] = Field(default_factory=list, description="Lists of component IDs in parallel")

class FlowData(BaseModel):
    current_paths: List[List[str]] = Field(default_factory=list, description="Paths from source to ground")
    upstream: Dict[str, List[str]] = Field(default_factory=dict, description="Components upstream of a given component")
    downstream: Dict[str, List[str]] = Field(default_factory=dict, description="Components downstream of a given component")
    polarity: Dict[str, str] = Field(default_factory=dict, description="Assigned polarity/direction for each component")

class TopologyLoop(BaseModel):
    id: str = Field(description="Unique loop identifier")
    components: List[str] = Field(description="List of component IDs in the loop")

class TopologyData(BaseModel):
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Node IDs and their connected pins")
    branches: List[Dict[str, Any]] = Field(default_factory=list, description="Branches between nodes")
    loops: List[TopologyLoop] = Field(default_factory=list, description="Fundamental loops (cycles) with IDs")

class CircuitKnowledge(CircuitAnalysis):
    topology: TopologyData = Field(default_factory=TopologyData)
    flow: FlowData = Field(default_factory=FlowData)
    grouping: GroupingData = Field(default_factory=GroupingData)
    equations: List[StructuredEquation] = Field(default_factory=list)
    learning_metadata: Dict[str, Any] = Field(default_factory=dict)
