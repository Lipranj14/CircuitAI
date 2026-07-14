"""
circuit_vision/svg_renderer.py — Clean SVG Schematic Generation

Renders a CircuitGraph into a clean, standardized SVG schematic.
Each component is drawn using predefined SVG symbol templates,
wires are rendered as orthogonal lines, and labels are placed
at their associated component positions.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Optional

from schemas.domain import CircuitGraph, DetectedComponent, WireSegment, Junction
from .config import (
    SVG_WIDTH,
    SVG_HEIGHT,
    SVG_COLORS,
    SVG_WIRE_STROKE_WIDTH,
    SVG_COMPONENT_STROKE_WIDTH,
    SVG_COMPONENT_SIZES,
    SVG_FONT_FAMILY,
    SVG_LABEL_FONT_SIZE,
    SVG_VALUE_FONT_SIZE,
    ComponentType,
)

logger = logging.getLogger(__name__)


# ============================================================
# SVG Symbol Templates (as path data)
# ============================================================

# Each symbol is defined as a function that takes (x, y, w, h) and
# returns a list of SVG element dicts: {tag, attrib, [children]}

def _svg_resistor(x: float, y: float, w: float, h: float) -> list[dict]:
    """Zigzag resistor symbol."""
    mid_y = y + h / 2
    points = (
        f"{x},{mid_y} {x + w * 0.18},{mid_y} "
        f"{x + w * 0.24},{y + h * 0.15} {x + w * 0.35},{y + h * 0.85} "
        f"{x + w * 0.46},{y + h * 0.15} {x + w * 0.57},{y + h * 0.85} "
        f"{x + w * 0.68},{y + h * 0.15} {x + w * 0.76},{y + h * 0.85} "
        f"{x + w * 0.82},{mid_y} {x + w},{mid_y}"
    )
    return [{"tag": "polyline", "attrib": {"points": points, "fill": "none"}}]


def _svg_capacitor(x: float, y: float, w: float, h: float) -> list[dict]:
    """Two parallel plates."""
    mid_y = y + h / 2
    plate_x1 = x + w * 0.4
    plate_x2 = x + w * 0.6
    return [
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(mid_y), "x2": str(plate_x1), "y2": str(mid_y)}},
        {"tag": "line", "attrib": {"x1": str(plate_x1), "y1": str(y + h * 0.1), "x2": str(plate_x1), "y2": str(y + h * 0.9)}},
        {"tag": "line", "attrib": {"x1": str(plate_x2), "y1": str(y + h * 0.1), "x2": str(plate_x2), "y2": str(y + h * 0.9)}},
        {"tag": "line", "attrib": {"x1": str(plate_x2), "y1": str(mid_y), "x2": str(x + w), "y2": str(mid_y)}},
    ]


def _svg_inductor(x: float, y: float, w: float, h: float) -> list[dict]:
    """Series of bumps."""
    mid_y = y + h / 2
    bumps = 4
    bw = w * 0.6 / bumps
    sx = x + w * 0.15
    path = f"M{x},{mid_y} L{sx},{mid_y} "
    for i in range(bumps):
        cx = sx + bw * (i + 0.5)
        path += f"C{sx + bw * i},{y + h * 0.1} {sx + bw * (i + 1)},{y + h * 0.1} {sx + bw * (i + 1)},{mid_y} "
    path += f"L{x + w},{mid_y}"
    return [{"tag": "path", "attrib": {"d": path, "fill": "none"}}]


def _svg_diode(x: float, y: float, w: float, h: float) -> list[dict]:
    """Triangle + bar diode symbol."""
    mid_y = y + h / 2
    tri_left = x + w * 0.3
    tri_right = x + w * 0.65
    return [
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(mid_y), "x2": str(tri_left), "y2": str(mid_y)}},
        {"tag": "polygon", "attrib": {"points": f"{tri_left},{y + h * 0.15} {tri_left},{y + h * 0.85} {tri_right},{mid_y}", "fill": "none"}},
        {"tag": "line", "attrib": {"x1": str(tri_right), "y1": str(y + h * 0.15), "x2": str(tri_right), "y2": str(y + h * 0.85)}},
        {"tag": "line", "attrib": {"x1": str(tri_right), "y1": str(mid_y), "x2": str(x + w), "y2": str(mid_y)}},
    ]


def _svg_led(x: float, y: float, w: float, h: float) -> list[dict]:
    """Diode with light arrows."""
    elements = _svg_diode(x, y, w, h)
    arr_x = x + w * 0.6
    arr_y = y + h * 0.1
    elements.extend([
        {"tag": "line", "attrib": {"x1": str(arr_x), "y1": str(arr_y), "x2": str(arr_x + 8), "y2": str(arr_y - 8), "stroke": "#f59e0b", "stroke-width": "1.5"}},
        {"tag": "line", "attrib": {"x1": str(arr_x + 5), "y1": str(arr_y + 3), "x2": str(arr_x + 13), "y2": str(arr_y - 5), "stroke": "#f59e0b", "stroke-width": "1.5"}},
    ])
    return elements


def _svg_battery(x: float, y: float, w: float, h: float) -> list[dict]:
    """Battery: alternating long/short plates."""
    mid_y = y + h / 2
    p1 = x + w * 0.35
    p2 = x + w * 0.45
    p3 = x + w * 0.55
    p4 = x + w * 0.65
    return [
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(mid_y), "x2": str(p1), "y2": str(mid_y)}},
        {"tag": "line", "attrib": {"x1": str(p1), "y1": str(y + h * 0.1), "x2": str(p1), "y2": str(y + h * 0.9)}},
        {"tag": "line", "attrib": {"x1": str(p2), "y1": str(y + h * 0.25), "x2": str(p2), "y2": str(y + h * 0.75)}},
        {"tag": "line", "attrib": {"x1": str(p3), "y1": str(y + h * 0.1), "x2": str(p3), "y2": str(y + h * 0.9)}},
        {"tag": "line", "attrib": {"x1": str(p4), "y1": str(y + h * 0.25), "x2": str(p4), "y2": str(y + h * 0.75)}},
        {"tag": "line", "attrib": {"x1": str(p4), "y1": str(mid_y), "x2": str(x + w), "y2": str(mid_y)}},
        {"tag": "text", "attrib": {"x": str(p1 + 2), "y": str(y + h * 0.08), "font-size": "10", "fill": "#22d3ee"}, "text": "+"},
    ]


def _svg_voltage_source(x: float, y: float, w: float, h: float) -> list[dict]:
    """Circle with +/- marks."""
    cx, cy = x + w / 2, y + h / 2
    r = min(w, h) * 0.35
    return [
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(cy), "x2": str(cx - r), "y2": str(cy)}},
        {"tag": "circle", "attrib": {"cx": str(cx), "cy": str(cy), "r": str(r), "fill": "none"}},
        {"tag": "text", "attrib": {"x": str(cx - 6), "y": str(cy - 2), "font-size": "10", "fill": "#22d3ee"}, "text": "+"},
        {"tag": "text", "attrib": {"x": str(cx + 2), "y": str(cy + 8), "font-size": "10", "fill": "#94a3b8"}, "text": "−"},
        {"tag": "line", "attrib": {"x1": str(cx + r), "y1": str(cy), "x2": str(x + w), "y2": str(cy)}},
    ]


def _svg_ground(x: float, y: float, w: float, h: float) -> list[dict]:
    """Three horizontal lines of decreasing width."""
    cx = x + w / 2
    return [
        {"tag": "line", "attrib": {"x1": str(cx), "y1": str(y), "x2": str(cx), "y2": str(y + h * 0.35)}},
        {"tag": "line", "attrib": {"x1": str(x + w * 0.15), "y1": str(y + h * 0.35), "x2": str(x + w * 0.85), "y2": str(y + h * 0.35)}},
        {"tag": "line", "attrib": {"x1": str(x + w * 0.25), "y1": str(y + h * 0.55), "x2": str(x + w * 0.75), "y2": str(y + h * 0.55)}},
        {"tag": "line", "attrib": {"x1": str(x + w * 0.35), "y1": str(y + h * 0.75), "x2": str(x + w * 0.65), "y2": str(y + h * 0.75)}},
    ]


def _svg_opamp(x: float, y: float, w: float, h: float) -> list[dict]:
    """Triangle with +/- input labels."""
    return [
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(y + h * 0.25), "x2": str(x + w * 0.2), "y2": str(y + h * 0.25)}},
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(y + h * 0.75), "x2": str(x + w * 0.2), "y2": str(y + h * 0.75)}},
        {"tag": "polygon", "attrib": {"points": f"{x + w * 0.2},{y} {x + w * 0.2},{y + h} {x + w * 0.88},{y + h / 2}", "fill": "none"}},
        {"tag": "text", "attrib": {"x": str(x + w * 0.24), "y": str(y + h * 0.32), "font-size": "10", "fill": "#ef4444"}, "text": "−"},
        {"tag": "text", "attrib": {"x": str(x + w * 0.24), "y": str(y + h * 0.82), "font-size": "10", "fill": "#22d3ee"}, "text": "+"},
        {"tag": "line", "attrib": {"x1": str(x + w * 0.88), "y1": str(y + h / 2), "x2": str(x + w), "y2": str(y + h / 2)}},
    ]


def _svg_transistor_npn(x: float, y: float, w: float, h: float) -> list[dict]:
    """NPN BJT with arrow on emitter."""
    bx = x + w * 0.35
    return [
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(y + h / 2), "x2": str(bx), "y2": str(y + h / 2)}},
        {"tag": "line", "attrib": {"x1": str(bx), "y1": str(y + h * 0.15), "x2": str(bx), "y2": str(y + h * 0.85)}},
        {"tag": "line", "attrib": {"x1": str(bx), "y1": str(y + h * 0.3), "x2": str(x + w * 0.8), "y2": str(y + h * 0.05)}},
        {"tag": "line", "attrib": {"x1": str(bx), "y1": str(y + h * 0.7), "x2": str(x + w * 0.8), "y2": str(y + h * 0.95)}},
        {"tag": "text", "attrib": {"x": str(x + w * 0.82), "y": str(y + h * 0.12), "font-size": "8", "fill": "#94a3b8"}, "text": "C"},
        {"tag": "text", "attrib": {"x": str(x + 2), "y": str(y + h * 0.45), "font-size": "8", "fill": "#94a3b8"}, "text": "B"},
        {"tag": "text", "attrib": {"x": str(x + w * 0.82), "y": str(y + h * 0.98), "font-size": "8", "fill": "#94a3b8"}, "text": "E"},
    ]


def _svg_transistor_pnp(x: float, y: float, w: float, h: float) -> list[dict]:
    """PNP BJT with arrow on emitter (reversed)."""
    return _svg_transistor_npn(x, y, w, h)  # Same shape, arrow direction handled by fill


def _svg_mosfet_n(x: float, y: float, w: float, h: float) -> list[dict]:
    """N-channel MOSFET."""
    gx = x + w * 0.35
    return [
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(y + h / 2), "x2": str(gx - 3), "y2": str(y + h / 2)}},
        {"tag": "line", "attrib": {"x1": str(gx), "y1": str(y + h * 0.15), "x2": str(gx), "y2": str(y + h * 0.85)}},
        {"tag": "line", "attrib": {"x1": str(gx + 4), "y1": str(y + h * 0.15), "x2": str(gx + 4), "y2": str(y + h * 0.35)}},
        {"tag": "line", "attrib": {"x1": str(gx + 4), "y1": str(y + h * 0.42), "x2": str(gx + 4), "y2": str(y + h * 0.58)}},
        {"tag": "line", "attrib": {"x1": str(gx + 4), "y1": str(y + h * 0.65), "x2": str(gx + 4), "y2": str(y + h * 0.85)}},
        {"tag": "line", "attrib": {"x1": str(gx + 4), "y1": str(y + h * 0.25), "x2": str(x + w * 0.8), "y2": str(y + h * 0.25)}},
        {"tag": "line", "attrib": {"x1": str(x + w * 0.8), "y1": str(y + h * 0.05), "x2": str(x + w * 0.8), "y2": str(y + h * 0.25)}},
        {"tag": "line", "attrib": {"x1": str(gx + 4), "y1": str(y + h * 0.75), "x2": str(x + w * 0.8), "y2": str(y + h * 0.75)}},
        {"tag": "line", "attrib": {"x1": str(x + w * 0.8), "y1": str(y + h * 0.75), "x2": str(x + w * 0.8), "y2": str(y + h * 0.95)}},
        {"tag": "text", "attrib": {"x": str(x + w * 0.83), "y": str(y + h * 0.12), "font-size": "7", "fill": "#94a3b8"}, "text": "D"},
        {"tag": "text", "attrib": {"x": str(x + 2), "y": str(y + h * 0.45), "font-size": "7", "fill": "#94a3b8"}, "text": "G"},
        {"tag": "text", "attrib": {"x": str(x + w * 0.83), "y": str(y + h * 0.98), "font-size": "7", "fill": "#94a3b8"}, "text": "S"},
    ]


def _svg_mosfet_p(x: float, y: float, w: float, h: float) -> list[dict]:
    """P-channel MOSFET (same shape, D/S swapped labels)."""
    elements = _svg_mosfet_n(x, y, w, h)
    # Swap D and S labels
    for elem in elements:
        if elem.get("text") == "D":
            elem["text"] = "S"
        elif elem.get("text") == "S":
            elem["text"] = "D"
    return elements


def _svg_switch(x: float, y: float, w: float, h: float) -> list[dict]:
    """Open switch symbol."""
    mid_y = y + h * 0.6
    return [
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(mid_y), "x2": str(x + w * 0.3), "y2": str(mid_y)}},
        {"tag": "circle", "attrib": {"cx": str(x + w * 0.3), "cy": str(mid_y), "r": "3", "fill": SVG_COLORS["component_stroke"]}},
        {"tag": "line", "attrib": {"x1": str(x + w * 0.3), "y1": str(mid_y), "x2": str(x + w * 0.7), "y2": str(y + h * 0.2)}},
        {"tag": "circle", "attrib": {"cx": str(x + w * 0.7), "cy": str(mid_y), "r": "3", "fill": SVG_COLORS["component_stroke"]}},
        {"tag": "line", "attrib": {"x1": str(x + w * 0.7), "y1": str(mid_y), "x2": str(x + w), "y2": str(mid_y)}},
    ]


def _svg_terminal(x: float, y: float, w: float, h: float) -> list[dict]:
    """Terminal node: circle with dot."""
    cx, cy = x + w / 2, y + h / 2
    return [
        {"tag": "circle", "attrib": {"cx": str(cx), "cy": str(cy), "r": str(min(w, h) * 0.3), "fill": "none"}},
        {"tag": "circle", "attrib": {"cx": str(cx), "cy": str(cy), "r": "3", "fill": SVG_COLORS["junction"]}},
    ]


def _svg_current_source(x: float, y: float, w: float, h: float) -> list[dict]:
    """Circle with arrow."""
    cx, cy = x + w / 2, y + h / 2
    r = min(w, h) * 0.35
    return [
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(cy), "x2": str(cx - r), "y2": str(cy)}},
        {"tag": "circle", "attrib": {"cx": str(cx), "cy": str(cy), "r": str(r), "fill": "none"}},
        {"tag": "line", "attrib": {"x1": str(cx - r * 0.5), "y1": str(cy), "x2": str(cx + r * 0.5), "y2": str(cy)}},
        {"tag": "line", "attrib": {"x1": str(cx + r), "y1": str(cy), "x2": str(x + w), "y2": str(cy)}},
    ]


def _svg_transformer(x: float, y: float, w: float, h: float) -> list[dict]:
    """Two coils with core lines."""
    elements = []
    # Left coil
    for i in range(3):
        cy = y + h * (0.2 + i * 0.25)
        elements.append({"tag": "path", "attrib": {
            "d": f"M{x + w * 0.1},{cy} C{x + w * 0.1},{cy - h * 0.1} {x + w * 0.3},{cy - h * 0.1} {x + w * 0.3},{cy}",
            "fill": "none"
        }})
    # Core lines
    elements.append({"tag": "line", "attrib": {"x1": str(x + w * 0.45), "y1": str(y + h * 0.1), "x2": str(x + w * 0.45), "y2": str(y + h * 0.9)}})
    elements.append({"tag": "line", "attrib": {"x1": str(x + w * 0.55), "y1": str(y + h * 0.1), "x2": str(x + w * 0.55), "y2": str(y + h * 0.9)}})
    # Right coil
    for i in range(3):
        cy = y + h * (0.2 + i * 0.25)
        elements.append({"tag": "path", "attrib": {
            "d": f"M{x + w * 0.7},{cy} C{x + w * 0.7},{cy - h * 0.1} {x + w * 0.9},{cy - h * 0.1} {x + w * 0.9},{cy}",
            "fill": "none"
        }})
    return elements


def _svg_ic(x: float, y: float, w: float, h: float) -> list[dict]:
    """IC / chip rectangle."""
    return [
        {"tag": "rect", "attrib": {"x": str(x + w * 0.15), "y": str(y + h * 0.1), "width": str(w * 0.7), "height": str(h * 0.8), "rx": "3", "fill": "none"}},
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(y + h * 0.3), "x2": str(x + w * 0.15), "y2": str(y + h * 0.3)}},
        {"tag": "line", "attrib": {"x1": str(x), "y1": str(y + h * 0.7), "x2": str(x + w * 0.15), "y2": str(y + h * 0.7)}},
        {"tag": "line", "attrib": {"x1": str(x + w * 0.85), "y1": str(y + h * 0.3), "x2": str(x + w), "y2": str(y + h * 0.3)}},
        {"tag": "line", "attrib": {"x1": str(x + w * 0.85), "y1": str(y + h * 0.7), "x2": str(x + w), "y2": str(y + h * 0.7)}},
    ]


# Registry mapping component type to SVG generator function
SVG_SYMBOL_REGISTRY: dict[str, callable] = {
    ComponentType.RESISTOR: _svg_resistor,
    ComponentType.CAPACITOR: _svg_capacitor,
    ComponentType.INDUCTOR: _svg_inductor,
    ComponentType.DIODE: _svg_diode,
    ComponentType.LED: _svg_led,
    ComponentType.BATTERY: _svg_battery,
    ComponentType.VOLTAGE_SOURCE: _svg_voltage_source,
    ComponentType.CURRENT_SOURCE: _svg_current_source,
    ComponentType.GROUND: _svg_ground,
    ComponentType.BJT_NPN: _svg_transistor_npn,
    ComponentType.BJT_PNP: _svg_transistor_pnp,
    ComponentType.MOSFET_N: _svg_mosfet_n,
    ComponentType.MOSFET_P: _svg_mosfet_p,
    ComponentType.OPAMP: _svg_opamp,
    ComponentType.SWITCH: _svg_switch,
    ComponentType.TRANSFORMER: _svg_transformer,
    ComponentType.TERMINAL: _svg_terminal,
    ComponentType.IC: _svg_ic,
}


# ============================================================
# SVG Renderer
# ============================================================

class SVGRenderer:
    """
    Renders a CircuitGraph into a clean, publication-quality SVG schematic.
    """

    def __init__(
        self,
        width: int = SVG_WIDTH,
        height: int = SVG_HEIGHT,
        dark_mode: bool = True,
    ):
        self.width = width
        self.height = height
        self.dark_mode = dark_mode

    def render(self, circuit: CircuitGraph) -> str:
        """
        Render the full circuit graph as an SVG string.

        Args:
            circuit: Complete CircuitGraph from the pipeline

        Returns:
            SVG markup string
        """
        # Calculate scale to fit circuit into SVG canvas
        scale_x = self.width / max(circuit.image_width, 1)
        scale_y = self.height / max(circuit.image_height, 1)
        scale = min(scale_x, scale_y, 1.5)  # Cap scaling to avoid oversizing

        # Build SVG document
        root = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": str(self.width),
            "height": str(self.height),
            "viewBox": f"0 0 {self.width} {self.height}",
            "font-family": SVG_FONT_FAMILY,
        })

        # Background
        if self.dark_mode:
            ET.SubElement(root, "rect", {
                "width": str(self.width),
                "height": str(self.height),
                "fill": SVG_COLORS["background"],
            })

        # Grid dots (subtle)
        self._draw_grid(root)

        # Wires layer (draw first so components overlay)
        wires_group = ET.SubElement(root, "g", {
            "id": "wires",
            "stroke": SVG_COLORS["wire"],
            "stroke-width": str(SVG_WIRE_STROKE_WIDTH),
            "stroke-linecap": "round",
        })
        for wire in circuit.wires:
            self._draw_wire(wires_group, wire, scale)

        # Junctions layer
        for junc in circuit.junctions:
            self._draw_junction(wires_group, junc, scale)

        # Components layer
        comps_group = ET.SubElement(root, "g", {
            "id": "components",
            "stroke": SVG_COLORS["component_stroke"],
            "stroke-width": str(SVG_COMPONENT_STROKE_WIDTH),
            "fill": "none",
        })
        for comp in circuit.components:
            self._draw_component(comps_group, comp, scale)

        # Labels layer
        labels_group = ET.SubElement(root, "g", {
            "id": "labels",
            "fill": SVG_COLORS["label"],
            "font-size": str(SVG_LABEL_FONT_SIZE),
        })
        for comp in circuit.components:
            self._draw_label(labels_group, comp, scale)

        # Convert to string
        return ET.tostring(root, encoding="unicode", xml_declaration=False)

    # ============================================================
    # Drawing Methods
    # ============================================================

    def _draw_grid(self, parent: ET.Element):
        """Draw subtle background grid dots."""
        grid_group = ET.SubElement(parent, "g", {
            "id": "grid",
            "fill": SVG_COLORS["grid"],
            "opacity": "0.3",
        })
        grid_spacing = 30
        for gx in range(0, self.width, grid_spacing):
            for gy in range(0, self.height, grid_spacing):
                ET.SubElement(grid_group, "circle", {
                    "cx": str(gx), "cy": str(gy), "r": "0.8",
                })

    def _draw_wire(self, parent: ET.Element, wire: WireSegment, scale: float):
        """Draw a single wire segment."""
        ET.SubElement(parent, "line", {
            "x1": str(wire.start.x * scale),
            "y1": str(wire.start.y * scale),
            "x2": str(wire.end.x * scale),
            "y2": str(wire.end.y * scale),
        })

    def _draw_junction(self, parent: ET.Element, junc: Junction, scale: float):
        """Draw a junction dot."""
        ET.SubElement(parent, "circle", {
            "cx": str(junc.position.x * scale),
            "cy": str(junc.position.y * scale),
            "r": "4",
            "fill": SVG_COLORS["junction"],
            "stroke": "none",
        })

    def _draw_component(self, parent: ET.Element, comp: DetectedComponent, scale: float):
        """Draw a component using its SVG symbol template."""
        comp_type = comp.type
        symbol_fn = SVG_SYMBOL_REGISTRY.get(comp_type)

        # Get symbol size
        size = SVG_COMPONENT_SIZES.get(comp_type, (60, 40))
        sw, sh = size

        # Position: center the symbol on the component's bounding box center
        cx = comp.bbox.center.x * scale
        cy = comp.bbox.center.y * scale
        sx = cx - sw / 2
        sy = cy - sh / 2

        # Create component group
        comp_group = ET.SubElement(parent, "g", {
            "id": f"comp_{comp.id}",
            "class": f"component {comp_type}",
        })

        if symbol_fn:
            elements = symbol_fn(sx, sy, sw, sh)
            for elem_def in elements:
                attrib = dict(elem_def.get("attrib", {}))
                # Apply default stroke/fill from parent if not specified
                if "stroke" not in attrib and elem_def["tag"] not in ("text",):
                    pass  # Inherits from parent group
                child = ET.SubElement(comp_group, elem_def["tag"], attrib)
                if "text" in elem_def:
                    child.text = elem_def["text"]
        else:
            # Fallback: draw a rectangle with component type label
            ET.SubElement(comp_group, "rect", {
                "x": str(sx), "y": str(sy),
                "width": str(sw), "height": str(sh),
                "rx": "4",
            })
            label = ET.SubElement(comp_group, "text", {
                "x": str(cx), "y": str(cy + 4),
                "text-anchor": "middle",
                "font-size": "10",
                "fill": SVG_COLORS["label"],
            })
            label.text = comp_type[:3].upper()

    def _draw_label(self, parent: ET.Element, comp: DetectedComponent, scale: float):
        """Draw component label text below the symbol."""
        if not comp.label:
            return

        cx = comp.bbox.center.x * scale
        size = SVG_COMPONENT_SIZES.get(comp.type, (60, 40))
        cy = comp.bbox.center.y * scale + size[1] / 2 + 14

        label_elem = ET.SubElement(parent, "text", {
            "x": str(cx),
            "y": str(cy),
            "text-anchor": "middle",
            "font-size": str(SVG_LABEL_FONT_SIZE),
            "font-weight": "bold",
        })
        label_elem.text = comp.label

        # Draw value below label if present
        if comp.value:
            value_elem = ET.SubElement(parent, "text", {
                "x": str(cx),
                "y": str(cy + SVG_VALUE_FONT_SIZE + 4),
                "text-anchor": "middle",
                "font-size": str(SVG_VALUE_FONT_SIZE),
                "fill": "#94a3b8",
            })
            value_elem.text = comp.value
