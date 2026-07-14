import logging
from typing import Optional

from core.logger import timed_execution
from core.exceptions import ReconstructionError
from schemas.domain import CircuitGraph, CircuitNode, DetectedComponent, WireSegment, Junction, Point, Pin

logger = logging.getLogger(__name__)


class GraphBuilderService:
    """Service responsible for reconstructing a CircuitGraph from detected components and AI-provided netlist."""

    @timed_execution("reconstruction")
    def build_graph(
        self, 
        components: list[DetectedComponent], 
        netlist_nodes: list[dict],
        labels: list, 
        img_w: int, 
        img_h: int
    ) -> CircuitGraph:
        """Build a CircuitGraph from components and AI-provided netlist nodes."""
        try:
            components = self._assign_electrical_ids(components)
            nodes = self._build_nodes_from_netlist(components, netlist_nodes)
            
            return CircuitGraph(
                components=components,
                wires=[],       # No wire segments — connectivity is in nodes
                junctions=[],
                nodes=nodes,
                labels=labels,
                image_width=img_w,
                image_height=img_h
            )
        except Exception as e:
            raise ReconstructionError(f"Failed to build circuit graph: {str(e)}", original_error=e)

    def _build_nodes_from_netlist(
        self, components: list[DetectedComponent], netlist_nodes: list[dict]
    ) -> list[CircuitNode]:
        """
        Build CircuitNode objects directly from the AI-provided netlist.
        No wire-to-pin matching needed — the AI already told us which pins connect.
        """
        nodes = []
        
        for node_data in netlist_nodes:
            node_id = node_data.get("id", f"N{len(nodes)+1}")
            connected_pins = node_data.get("pins", [])
            
            # Determine label
            node_label = None
            if node_id == "GND" or node_id.startswith("GND"):
                node_label = "GND"
            
            # Validate that referenced pins actually exist
            valid_pins = []
            for pin_ref in connected_pins:
                parts = pin_ref.split(".", 1)
                if len(parts) != 2:
                    logger.warning(f"Invalid pin reference: {pin_ref}")
                    continue
                comp_id, pin_name = parts
                # Find the component
                comp = next((c for c in components if c.id == comp_id), None)
                if comp is None:
                    logger.warning(f"Component {comp_id} not found for pin {pin_ref}")
                    continue
                # Ensure pin exists on the component
                pin_exists = any(p.name == pin_name for p in comp.pins)
                if not pin_exists:
                    # Auto-create the pin
                    comp.pins.append(Pin(
                        name=pin_name, 
                        x=comp.bbox.x + comp.bbox.w / 2, 
                        y=comp.bbox.y + comp.bbox.h / 2
                    ))
                valid_pins.append(pin_ref)
            
            if len(valid_pins) >= 2:
                nodes.append(CircuitNode(
                    id=node_id, 
                    connected_pins=valid_pins, 
                    label=node_label
                ))
                
                # Update pin.connected_node on each component
                for pin_ref in valid_pins:
                    comp_id, pin_name = pin_ref.split(".", 1)
                    for comp in components:
                        if comp.id == comp_id:
                            for p in comp.pins:
                                if p.name == pin_name:
                                    p.connected_node = node_id

        logger.info(f"Built {len(nodes)} circuit nodes from AI netlist")
        return nodes

    @staticmethod
    def _find_node_label(pin_keys: list[str], components: list[DetectedComponent]) -> Optional[str]:
        for key in pin_keys:
            comp_id = key.split(".")[0]
            for comp in components:
                if comp.id == comp_id:
                    if comp.type == "ground": return "GND"
                    if comp.type == "terminal" and comp.label: return comp.label
        return None

    @staticmethod
    def _assign_electrical_ids(components: list[DetectedComponent]) -> list[DetectedComponent]:
        """Only assign IDs if they haven't been assigned already (by detector_service)."""
        # Check if IDs are already electrical (V1, R1, etc.)
        if components and not components[0].id.startswith("comp_"):
            return components  # Already assigned

        counts = {}
        prefix_map = {
            "resistor": "R", "battery": "V", "voltage_source": "V", "dc_source": "V",
            "current_source": "I", "capacitor": "C", "inductor": "L", "diode": "D",
            "led": "D", "switch": "SW", "opamp": "OP", "ground": "GND",
            "transistor_npn": "Q", "transistor_pnp": "Q", "mosfet_n": "M", "mosfet_p": "M",
        }
        for comp in components:
            ctype = comp.type.lower()
            prefix = prefix_map.get(ctype, "U")
            counts[prefix] = counts.get(prefix, 0) + 1
            comp.id = f"{prefix}{counts[prefix]}"
            if not comp.label:
                comp.label = comp.id
        return components

    def to_react_flow(self, circuit: CircuitGraph) -> tuple[list[dict], list[dict]]:
        """Convert circuit graph to React Flow nodes and edges."""
        rf_nodes = []
        for comp in circuit.components:
            rf_nodes.append({
                "id": comp.id,
                "type": "component",
                "position": {"x": comp.bbox.x * 3, "y": comp.bbox.y * 3},
                "data": {
                    "label": comp.label or comp.id,
                    "value": comp.value,
                    "componentType": comp.type,
                }
            })

        rf_edges = []
        for node in circuit.nodes:
            pins = node.connected_pins
            for i in range(len(pins)):
                for j in range(i + 1, len(pins)):
                    src_comp, src_pin = pins[i].split(".", 1)
                    tgt_comp, tgt_pin = pins[j].split(".", 1)
                    if src_comp == tgt_comp:
                        continue
                    
                    # Basic heuristic to map pin names to physical handle positions
                    def get_handle(comp_id, pin_name):
                        comp_type = next((c.type for c in circuit.components if c.id == comp_id), "resistor")
                        if comp_type in ["battery", "voltage_source", "dc_source", "capacitor"]:
                            return "top" if pin_name == "pin1" else "bottom"
                        if comp_type == "ground":
                            return "top"
                        return "left" if pin_name == "pin1" else "right"

                    edge_id = f"e-{src_comp}.{src_pin}-{tgt_comp}.{tgt_pin}"
                    
                    rf_edges.append({
                        "id": edge_id,
                        "source": src_comp,
                        "sourceHandle": get_handle(src_comp, src_pin),
                        "target": tgt_comp,
                        "targetHandle": get_handle(tgt_comp, tgt_pin),
                        "type": "step",
                    })

        return rf_nodes, rf_edges
