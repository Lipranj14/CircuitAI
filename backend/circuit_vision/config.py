"""
circuit_vision/config.py — Central Configuration

All constants, thresholds, model paths, component registries, and
SVG rendering parameters for the circuit recognition pipeline.
"""

from pathlib import Path
from enum import Enum

# ============================================================
# Paths
# ============================================================

# Root of the backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Directory for ML model weights (YOLO, etc.)
MODELS_DIR = BACKEND_DIR / "models"

# YOLOv8 weights file (when custom-trained)
YOLO_WEIGHTS_PATH = MODELS_DIR / "circuit_yolov8m.pt"

# ============================================================
# Component Type Registry
# ============================================================

class ComponentType(str, Enum):
    """All supported electrical component types."""
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    DIODE = "diode"
    LED = "led"
    BATTERY = "battery"
    VOLTAGE_SOURCE = "voltage_source"
    CURRENT_SOURCE = "current_source"
    GROUND = "ground"
    BJT_NPN = "transistor_npn"
    BJT_PNP = "transistor_pnp"
    MOSFET_N = "mosfet_n"
    MOSFET_P = "mosfet_p"
    OPAMP = "opamp"
    SWITCH = "switch"
    TRANSFORMER = "transformer"
    TERMINAL = "terminal"
    IC = "ic"

# Number of pins for each component type
COMPONENT_PIN_COUNT: dict[str, int] = {
    ComponentType.RESISTOR: 2,
    ComponentType.CAPACITOR: 2,
    ComponentType.INDUCTOR: 2,
    ComponentType.DIODE: 2,
    ComponentType.LED: 2,
    ComponentType.BATTERY: 2,
    ComponentType.VOLTAGE_SOURCE: 2,
    ComponentType.CURRENT_SOURCE: 2,
    ComponentType.GROUND: 1,
    ComponentType.BJT_NPN: 3,       # Base, Collector, Emitter
    ComponentType.BJT_PNP: 3,
    ComponentType.MOSFET_N: 3,      # Gate, Drain, Source
    ComponentType.MOSFET_P: 3,
    ComponentType.OPAMP: 3,         # +, -, Out (ignoring V+/V-)
    ComponentType.SWITCH: 2,
    ComponentType.TRANSFORMER: 4,   # Primary+, Primary-, Secondary+, Secondary-
    ComponentType.TERMINAL: 1,
    ComponentType.IC: 4,            # Variable, default to 4
}

# Human-readable display names
COMPONENT_DISPLAY_NAMES: dict[str, str] = {
    ComponentType.RESISTOR: "Resistor",
    ComponentType.CAPACITOR: "Capacitor",
    ComponentType.INDUCTOR: "Inductor",
    ComponentType.DIODE: "Diode",
    ComponentType.LED: "LED",
    ComponentType.BATTERY: "Battery",
    ComponentType.VOLTAGE_SOURCE: "Voltage Source",
    ComponentType.CURRENT_SOURCE: "Current Source",
    ComponentType.GROUND: "Ground",
    ComponentType.BJT_NPN: "NPN Transistor",
    ComponentType.BJT_PNP: "PNP Transistor",
    ComponentType.MOSFET_N: "N-Channel MOSFET",
    ComponentType.MOSFET_P: "P-Channel MOSFET",
    ComponentType.OPAMP: "Op-Amp",
    ComponentType.SWITCH: "Switch",
    ComponentType.TRANSFORMER: "Transformer",
    ComponentType.TERMINAL: "Terminal",
    ComponentType.IC: "Integrated Circuit",
}

# ============================================================
# Detection Thresholds
# ============================================================

# Minimum confidence for YOLO detection to accept a component
YOLO_CONFIDENCE_THRESHOLD = 0.35

# Minimum confidence for OCR text to be considered a valid label
OCR_CONFIDENCE_THRESHOLD = 0.5

# Maximum pixel distance to associate a text label with a component
LABEL_ASSOCIATION_MAX_DISTANCE = 80  # pixels

# Maximum pixel distance to consider a wire endpoint connected to a pin
PIN_WIRE_PROXIMITY_THRESHOLD = 45  # pixels

# Minimum line length for Hough transform to detect as a wire
MIN_WIRE_LENGTH = 20  # pixels

# ============================================================
# Preprocessing Parameters
# ============================================================

# Maximum image dimension (longer edge) after resize
MAX_IMAGE_DIMENSION = 1600

# Adaptive threshold block size (must be odd)
ADAPTIVE_THRESH_BLOCK_SIZE = 15

# Adaptive threshold constant subtracted from mean
ADAPTIVE_THRESH_C = 10

# Morphological kernel size for denoising
MORPH_KERNEL_SIZE = 3

# ============================================================
# SVG Rendering Constants
# ============================================================

# Canvas size for SVG output
SVG_WIDTH = 1200
SVG_HEIGHT = 800

# Default colors
SVG_COLORS = {
    "background": "#0f172a",
    "wire": "#3b82f6",
    "junction": "#22d3ee",
    "label": "#f8fafc",
    "component_stroke": "#e2e8f0",
    "component_fill": "none",
    "grid": "#1e293b",
}

# Stroke widths
SVG_WIRE_STROKE_WIDTH = 2.0
SVG_COMPONENT_STROKE_WIDTH = 2.0

# Component symbol dimensions (width, height) in SVG units
SVG_COMPONENT_SIZES: dict[str, tuple[int, int]] = {
    ComponentType.RESISTOR: (80, 40),
    ComponentType.CAPACITOR: (60, 40),
    ComponentType.INDUCTOR: (80, 40),
    ComponentType.DIODE: (60, 40),
    ComponentType.LED: (60, 40),
    ComponentType.BATTERY: (60, 40),
    ComponentType.VOLTAGE_SOURCE: (60, 50),
    ComponentType.CURRENT_SOURCE: (60, 50),
    ComponentType.GROUND: (40, 40),
    ComponentType.BJT_NPN: (60, 60),
    ComponentType.BJT_PNP: (60, 60),
    ComponentType.MOSFET_N: (60, 60),
    ComponentType.MOSFET_P: (60, 60),
    ComponentType.OPAMP: (80, 60),
    ComponentType.SWITCH: (60, 40),
    ComponentType.TRANSFORMER: (60, 50),
    ComponentType.TERMINAL: (30, 30),
    ComponentType.IC: (60, 50),
}

# Font settings
SVG_FONT_FAMILY = "monospace"
SVG_LABEL_FONT_SIZE = 12
SVG_VALUE_FONT_SIZE = 10

# ============================================================
# Ollama Configuration
# ============================================================
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_VISION_MODEL = "llava"
OLLAMA_TEXT_MODEL = "llama3.1"

# Single-pass circuit detection prompt
OLLAMA_SINGLE_PASS_PROMPT = """CRITICAL: Read the exact text labels on each component in the image. If you see text like 5V, 1k, 100uF next to a component, that is its value. Include it in the value field.

Analyze this circuit diagram image carefully.

STEP 1 - List every component you see. For each component:
- Read the label (R1, V1, D1, C1, etc.) directly from the image text
- Read the value (5V, 1k, 100uF, etc.) directly from the image text
- Identify the type from the symbol shape

STEP 2 - Trace every wire. For each wire:
- Start at one component terminal
- Follow the wire path
- End at the next component terminal or junction
- Every junction where 2+ wires meet is a node

STEP 3 - Build the node list. Rules:
- Every component terminal must connect to exactly one node
- Voltage source negative terminal ALWAYS connects to GND node
- GND symbol always belongs to node_gnd
- Series components share exactly one node between them

STEP 4 - Verify: count that every component appears in at least 2 connections.

Return ONLY this JSON, no explanation, no markdown:
{
  "components": [
    {"id": "V1", "type": "voltage_source", "value": "5V"},
    {"id": "R1", "type": "resistor", "value": "1k"},
    {"id": "D1", "type": "diode", "value": ""},
    {"id": "GND", "type": "ground", "value": ""}
  ],
  "nodes": [
    {"id": "node_1", "connected_components": ["V1", "R1"]},
    {"id": "node_2", "connected_components": ["R1", "D1"]},
    {"id": "node_gnd", "connected_components": ["D1", "GND", "V1"]}
  ],
  "connections": [
    {"from": "V1.positive", "to": "node_1"},
    {"from": "V1.negative", "to": "node_gnd"},
    {"from": "R1.pin1", "to": "node_1"},
    {"from": "R1.pin2", "to": "node_2"},
    {"from": "D1.anode", "to": "node_2"},
    {"from": "D1.cathode", "to": "node_gnd"},
    {"from": "GND.pin1", "to": "node_gnd"}
  ]
}

The above is FORMAT ONLY. Analyze the actual image. Return only JSON."""

# Tutor system prompt
OLLAMA_TUTOR_SYSTEM_PROMPT = """You are an expert ECE tutor helping a student analyze a circuit using Socratic method.

Rules you must follow:
1. NEVER give the final answer directly
2. Ask leading questions that guide the student to discover the answer themselves
3. When referencing a component or node, always use its exact ID (e.g., R1, node_1) so the UI can highlight it
4. Always explain WHY a law applies, not just THAT it applies
5. If the student makes a conceptual error, address the misconception before continuing
6. Keep all explanations tied to the specific circuit provided

Response format — always return valid JSON:
{
  "message": "your tutoring response here",
  "highlight": ["R1", "node_1"],
  "equation": "V = IR (optional LaTeX, empty string if not needed)",
  "hint_level": 1
}

hint_level: 1 = subtle nudge, 2 = moderate hint, 3 = direct guidance"""

