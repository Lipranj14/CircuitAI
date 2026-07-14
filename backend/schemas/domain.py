"""
circuit_vision/schemas.py — Pydantic Data Models

Defines the complete type system for the circuit recognition pipeline.
Every data structure flowing between pipeline stages is typed here.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Any


# ============================================================
# Geometry Primitives
# ============================================================

class Point(BaseModel):
    """A 2D point in image pixel coordinates."""
    x: float
    y: float


class BoundingBox(BaseModel):
    """Axis-aligned bounding box in image pixel coordinates."""
    x: float = Field(description="Left edge x-coordinate")
    y: float = Field(description="Top edge y-coordinate")
    w: float = Field(description="Width")
    h: float = Field(description="Height")

    @property
    def center(self) -> Point:
        """Center point of the bounding box."""
        return Point(x=self.x + self.w / 2, y=self.y + self.h / 2)

    @property
    def area(self) -> float:
        return self.w * self.h


# ============================================================
# Pin (Connection Point on a Component)
# ============================================================

class Pin(BaseModel):
    """A connection point (terminal) on a component."""
    name: str = Field(description="Pin identifier, e.g. 'pin1', 'base', 'gate'")
    x: float = Field(description="Pin x-coordinate in image space")
    y: float = Field(description="Pin y-coordinate in image space")
    connected_node: Optional[str] = Field(
        default=None,
        description="Node ID this pin is electrically connected to"
    )


# ============================================================
# Detected Component
# ============================================================

class DetectedComponent(BaseModel):
    """A single electrical component detected in the circuit diagram."""
    id: str = Field(description="Unique component identifier")
    type: str = Field(description="Component type (resistor, capacitor, etc.)")
    label: Optional[str] = Field(
        default=None,
        description="Text label from diagram (R1, C1, OP1, etc.)"
    )
    value: Optional[str] = Field(
        default=None,
        description="Component value (1k, 10uF, 9V, etc.)"
    )
    bbox: BoundingBox = Field(description="Bounding box in image coordinates")
    pins: list[Pin] = Field(
        default_factory=list,
        description="Connection points on this component"
    )
    confidence: float = Field(
        default=1.0,
        description="Detection confidence score [0.0, 1.0]"
    )
    source: str = Field(
        default="gemini",
        description="Detection source: 'gemini', 'yolo', 'manual'"
    )


# ============================================================
# Detected Text Label
# ============================================================

class DetectedLabel(BaseModel):
    """A text label detected by OCR in the circuit diagram."""
    text: str = Field(description="Recognized text content")
    position: Point = Field(description="Center position of text region")
    bbox: BoundingBox = Field(description="Bounding box of text region")
    confidence: float = Field(
        default=1.0,
        description="OCR confidence score [0.0, 1.0]"
    )
    associated_component_id: Optional[str] = Field(
        default=None,
        description="ID of the component this label belongs to"
    )


# ============================================================
# Wire & Junction
# ============================================================

class WireSegment(BaseModel):
    """A single wire segment connecting two points."""
    id: str = Field(description="Unique wire identifier")
    start: Point = Field(description="Start point of wire segment")
    end: Point = Field(description="End point of wire segment")
    wire_type: str = Field(
        default="straight",
        description="Wire geometry: 'horizontal', 'vertical', 'diagonal', 'straight'"
    )


class Junction(BaseModel):
    """A junction point where 3+ wires meet."""
    id: str = Field(description="Unique junction identifier")
    position: Point = Field(description="Junction location")
    connected_wire_ids: list[str] = Field(
        default_factory=list,
        description="IDs of wires meeting at this junction"
    )


# ============================================================
# Circuit Node (Electrical Net)
# ============================================================

class CircuitNode(BaseModel):
    """
    An electrical node (net) — a set of pins that are
    electrically connected to each other via wires.
    """
    id: str = Field(description="Unique node identifier (e.g. 'N1', 'GND')")
    connected_pins: list[str] = Field(
        default_factory=list,
        description="List of pin references: 'component_id.pin_name'"
    )
    label: Optional[str] = Field(
        default=None,
        description="Node label if named (e.g. 'VCC', 'GND', 'Vin')"
    )


# ============================================================
# Full Circuit Graph (Pipeline Output)
# ============================================================

class CircuitGraph(BaseModel):
    """
    Complete structured representation of a circuit diagram.
    This is the primary output of the recognition pipeline.
    """
    components: list[DetectedComponent] = Field(
        default_factory=list,
        description="All detected electrical components"
    )
    wires: list[WireSegment] = Field(
        default_factory=list,
        description="All detected wire segments"
    )
    junctions: list[Junction] = Field(
        default_factory=list,
        description="All detected wire junctions"
    )
    nodes: list[CircuitNode] = Field(
        default_factory=list,
        description="Electrical nodes (nets) grouping connected pins"
    )
    labels: list[DetectedLabel] = Field(
        default_factory=list,
        description="All detected text labels"
    )
    image_width: int = Field(default=0, description="Original image width in pixels")
    image_height: int = Field(default=0, description="Original image height in pixels")

    @property
    def component_count(self) -> int:
        return len(self.components)

    @property
    def connection_count(self) -> int:
        return len(self.wires)

    def get_component_by_id(self, component_id: str) -> Optional[DetectedComponent]:
        """Look up a component by its ID."""
        for comp in self.components:
            if comp.id == component_id:
                return comp
        return None

    def get_components_by_type(self, comp_type: str) -> list[DetectedComponent]:
        """Get all components of a specific type."""
        return [c for c in self.components if c.type == comp_type]

class CircuitAnalysis(BaseModel):
    """
    Deterministic electrical analysis of a CircuitGraph.
    Computed algebraically from graph topology.
    """
    circuit_type: str = Field(default="Unknown", description="e.g. 'DC Resistive', 'RLC', 'Diode Circuit'")
    difficulty: str = Field(default="Unknown", description="e.g. 'Beginner', 'Intermediate', 'Advanced'")
    component_count: int = Field(default=0)
    node_count: int = Field(default=0)
    branch_count: int = Field(default=0)
    loop_count: int = Field(default=0)
    applicable_laws: list[str] = Field(default_factory=list, description="e.g. ['Ohm\\'s Law', 'KVL']")
    candidate_equations: list[str] = Field(default_factory=list, description="e.g. ['V = I * R']")


# ============================================================
# Auto-Repair Models
# ============================================================

class RepairAction(BaseModel):
    """Programmatic action to repair a circuit."""
    action_type: str = Field(description="Type of fix (e.g. 'add_connection')")
    source_pin: str = Field(description="Source pin, e.g. 'LED1.pin2'")
    target_node: str = Field(description="Target electrical node ID, e.g. '0' or 'N1'")

class RepairSuggestion(BaseModel):
    """A suggested automatic repair for a broken circuit."""
    id: str = Field(description="Unique ID for the suggestion")
    description: str = Field(description="Short action description, e.g. 'Connect LED to Ground'")
    reason: str = Field(description="Why this repair is necessary")
    actions: list[RepairAction] = Field(default_factory=list)
    visual_hints: list[str] = Field(
        default_factory=list,
        description="Component IDs to highlight on the frontend"
    )

class ValidationCheck(BaseModel):
    id: str = Field(description="Unique check identifier")
    name: str = Field(description="Rule name (e.g., 'Ground Check')")
    status: str = Field(description="'pass', 'warning', or 'error'")
    description: str = Field(description="Explanation of the issue or confirmation of pass")
    visual_hints: list[str] = Field(default_factory=list, description="Component IDs to highlight")
    repair: Optional[RepairSuggestion] = Field(default=None, description="1-Click repair if applicable")

class ValidationReport(BaseModel):
    is_valid: bool = Field(description="True if no errors were found")
    checks: list[ValidationCheck] = Field(default_factory=list)

# ============================================================
# API Response Models
# ============================================================

class AnalysisResponse(BaseModel):
    """Response from the /api/analyze-circuit-v2 endpoint."""
    status: str = Field(default="success")
    circuit: CircuitGraph = Field(description="Full circuit graph")
    svg: str = Field(default="", description="Reconstructed SVG schematic")
    # React Flow compatible format for the frontend
    react_flow_nodes: list[dict] = Field(
        default_factory=list,
        description="Nodes formatted for React Flow"
    )
    react_flow_edges: list[dict] = Field(
        default_factory=list,
        description="Edges formatted for React Flow"
    )
    analysis: Optional[CircuitAnalysis] = Field(default=None, description="Deterministic topological analysis")
    repairs: list[RepairSuggestion] = Field(
        default_factory=list,
        description="Auto-repair suggestions for faulty circuits"
    )
    fallback: bool = Field(default=False, description="Indicates fallback mock data due to API quota limits")

class ComponentEducationalDetails(BaseModel):
    name: str = Field(description="Proper electrical name, e.g., 'Resistor', 'Voltage Source'")
    purpose: str = Field(description="General purpose of this type of component")
    function_in_circuit: str = Field(description="Specific role in the current circuit")
    related_equations: list[str] = Field(description="Equations relevant to this component")
    common_mistakes: list[str] = Field(description="Common student misconceptions or mistakes")

class SuggestedQuestionsResponse(BaseModel):
    questions: list[str] = Field(description="List of AI-generated questions to guide the student")

class ComponentMetadataRequest(BaseModel):
    comp_id: str
    comp_type: str
    analysis: CircuitAnalysis

class SuggestedQuestionsRequest(BaseModel):
    analysis: CircuitAnalysis


class SVGResponse(BaseModel):
    """Response for SVG-only endpoints."""
    svg: str = Field(description="SVG markup string")
    width: int = Field(description="SVG width")
    height: int = Field(description="SVG height")

class SimulationRequest(BaseModel):
    """Request payload for the simulation endpoint."""
    circuit: CircuitGraph = Field(description="The parsed circuit graph to simulate")
    analysis_type: str = Field(
        default="dc",
        description="Type of analysis: 'dc', 'ac', or 'transient'"
    )
    time_step: float = Field(default=1e-6, description="Step time for transient analysis (seconds)")
    end_time: float = Field(default=1e-3, description="End time for transient analysis (seconds)")
    start_freq: float = Field(default=1.0, description="Start frequency for AC analysis (Hz)")
    stop_freq: float = Field(default=1e6, description="Stop frequency for AC analysis (Hz)")
    points_per_decade: int = Field(default=10, description="Points per decade for AC analysis")

class SimulationResponse(BaseModel):
    """Response payload containing simulation results."""
    status: str = Field(default="success")
    analysis_type: str = Field(description="Type of analysis performed")
    time: list[float] = Field(default_factory=list, description="Time points (for transient analysis)")
    frequency: list[float] = Field(default_factory=list, description="Frequency points (for AC analysis)")
    nodes: dict[str, list[float]] = Field(
        default_factory=dict,
        description="Voltages at each node across the simulation domain"
    )
    branch_currents: dict[str, list[float]] = Field(
        default_factory=dict,
        description="Currents through voltage sources or specific branches"
    )
    node_connections: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of SPICE node names to component pins"
    )
    error_message: Optional[str] = Field(default=None, description="Error message if simulation failed")

class ChatMessage(BaseModel):
    """A single message in the tutor chat history."""
    role: str = Field(description="'user' or 'assistant'")
    content: str = Field(description="Message text")

class TutorRequest(BaseModel):
    """Request payload for the AI Circuit Tutor endpoint."""
    query: str = Field(description="The user's question")
    chat_history: list[ChatMessage] = Field(
        default_factory=list, 
        description="Previous conversation context"
    )
    expertise_level: str = Field(
        default="intermediate",
        description="'beginner', 'intermediate', or 'advanced'"
    )
    circuit: CircuitGraph = Field(description="The logical circuit structure")
    knowledge: Any = Field(default=None, description="Deterministic CircuitKnowledge from the backend pipeline")
    simulation_data: Optional[SimulationResponse] = Field(
        default=None,
        description="Results from the most recent simulation (if available)"
    )

class QuizQuestion(BaseModel):
    """An interactive conceptual quiz question."""
    question: str = Field(description="The question text")
    options: list[str] = Field(description="List of possible answers (max 4)")
    correct_option_index: int = Field(description="Index of the correct answer (0-based)")
    explanation: str = Field(description="Why this answer is correct")

class HighlightElement(BaseModel):
    type: str = Field(description="'component', 'node', or 'loop'")
    id: str = Field(description="ID of the element")

class TutorResponse(BaseModel):
    """Response payload from the AI Circuit Tutor."""
    message: str = Field(description="The pedagogical explanation in markdown format")
    highlight_components: list[str] = Field(
        default_factory=list,
        description="List of component IDs to highlight on the UI canvas"
    )
    highlight_elements: list[HighlightElement] = Field(
        default_factory=list,
        description="Structured list of elements (components, nodes, loops) to highlight"
    )
    quiz: Optional[QuizQuestion] = Field(
        default=None,
        description="An optional conceptual follow-up question"
    )

