"""
circuit_vision/component_detector.py — 3-Pass Circuit Detection Pipeline

Pass 1: Component Detection — identifies component types, labels, values, bounding boxes
Pass 2: Netlist Extraction — determines logical connectivity from the image
Pass 3: Netlist Validation — verifies and corrects the netlist

Uses the google-genai SDK (replaces deprecated google-generativeai).
"""

# SPATIAL DATA NOTE: Bounding boxes are dummy grid coordinates.
# LLaVA single-pass prompt does not return spatial positions.
# To restore real spatial data in future:
#   1. Add bbox request back to OLLAMA_SINGLE_PASS_PROMPT
#   2. Replace grid_layout_coordinates() with parsed bbox values
#   3. Re-enable PaddleOCR label association

import os
import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from PIL import Image
import numpy as np

from schemas.domain import DetectedComponent, BoundingBox, Pin, Point
from circuit_vision.debug_store import store_last_parse_result
from .config import (
    OLLAMA_SINGLE_PASS_PROMPT,
    YOLO_WEIGHTS_PATH,
    YOLO_CONFIDENCE_THRESHOLD,
    COMPONENT_PIN_COUNT,
    ComponentType,
)

logger = logging.getLogger(__name__)

def auto_repair_circuit(components: list, nodes: list, connections: list) -> dict:
    """
    Automatically repairs common circuit graph errors:
    - Voltage sources with unconnected negative terminal → connect to GND
    - Components that appear in connections but not in nodes → add to nearest node
    - Missing GND node → create one and connect it
    - Orphaned components → connect to most likely node based on component type
    """
    comp_ids = {c["id"] for c in components}
    node_map = {n["id"]: n["connected_components"] for n in nodes}

    # Track which terminals are connected per component
    connected_terminals = {}
    for conn in connections:
        comp = conn["from"].split(".")[0]
        terminal = conn["from"].split(".")[-1] if "." in conn["from"] else "pin1"
        if comp in comp_ids:
            if comp not in connected_terminals:
                connected_terminals[comp] = set()
            connected_terminals[comp].add(terminal)

    # Rule 1: Every voltage source must have both positive and negative connected
    for comp in components:
        if comp["type"] == "voltage_source":
            terminals = connected_terminals.get(comp["id"], set())
            if "negative" not in terminals and "pin2" not in terminals:
                # Find or create GND node
                gnd_node = next(
                    (n for n in nodes if "gnd" in n["id"].lower() or
                     "GND" in n.get("connected_components", [])), None
                )
                if gnd_node:
                    if comp["id"] not in gnd_node["connected_components"]:
                        gnd_node["connected_components"].append(comp["id"])
                    connections.append({
                        "from": f"{comp['id']}.negative",
                        "to": gnd_node["id"]
                    })
                else:
                    # Create GND node
                    nodes.append({
                        "id": "node_gnd",
                        "connected_components": [comp["id"], "GND"]
                    })
                    connections.append({
                        "from": f"{comp['id']}.negative",
                        "to": "node_gnd"
                    })
                print(f"[AUTO-REPAIR] Connected {comp['id']}.negative to GND node")

    # Rule 2: Every component must appear in at least one node
    all_node_comps = set()
    for n in nodes:
        all_node_comps.update(n.get("connected_components", []))

    for comp in components:
        if comp["id"] not in all_node_comps:
            # Find which node this component connects to from connections list
            for conn in connections:
                from_comp = conn["from"].split(".")[0]
                to_comp = conn["to"].split(".")[0]
                if from_comp == comp["id"] and to_comp in node_map:
                    node_map[to_comp].append(comp["id"])
                    print(f"[AUTO-REPAIR] Added {comp['id']} to node {to_comp}")
                    break
            else:
                # Last resort: add to first available node
                if nodes:
                    nodes[0]["connected_components"].append(comp["id"])
                    print(f"[AUTO-REPAIR] Force-connected orphan {comp['id']} to {nodes[0]['id']}")

    # Rule 3: Extract and preserve component values
    # Values should come from Gemini JSON — if empty, flag for user to fill
    for comp in components:
        if not comp.get("value"):
            comp["value"] = ""
            comp["value_missing"] = True
            print(f"[AUTO-REPAIR] Component {comp['id']} has no value — user input needed")
    # Rule 4: Any node with only 1 connected component is floating
    # Find its other connection from the connections list and add it
    for node in nodes:
        if len(node.get("connected_components", [])) < 2:
            node_id = node["id"]
            # Find all connections that reference this node
            connected_to_node = [
                conn for conn in connections
                if conn.get("to") == node_id or conn.get("from") == node_id
            ]
            for conn in connected_to_node:
                # Get the component on the other end
                from_comp = conn["from"].split(".")[0]
                to_comp = conn["to"].split(".")[0]
                # Add whichever one isn't already in the node
                for comp_id in [from_comp, to_comp]:
                    if (comp_id in comp_ids and
                        comp_id not in node["connected_components"]):
                        node["connected_components"].append(comp_id)
                        print(f"[AUTO-REPAIR] Fixed floating node {node_id}: added {comp_id}")
    return {
        "components": components,
        "nodes": nodes,
        "connections": connections,
        "repaired": True
    }

class ComponentDetector:
    """
    3-pass circuit detection pipeline using Gemini VLM.

    Pass 1: Detect components (type, label, value, bounding box)
    Pass 2: Extract netlist (which pins are connected)
    Pass 3: Validate and correct the netlist
    """

    def __init__(self, use_yolo: bool = False):
        self.use_yolo = use_yolo and YOLO_WEIGHTS_PATH.exists()
        self._yolo_model = None
        self._genai_client = None

        if self.use_yolo:
            self._load_yolo()
        else:
            self._load_vision_model()

    # ============================================================
    # Vision Model Initialization
    # ============================================================

    def _load_vision_model(self):
        """No-op. Gemini API does not require initialization."""
        logger.info("Gemini Vision API ready.")

    # ============================================================
    # Public API
    # ============================================================

    async def detect(
        self,
        image: np.ndarray,
        image_pil: Optional[Image.Image] = None,
    ) -> tuple[list[DetectedComponent], list[dict], list[dict]]:
        """
        Pass 1: Detect all electrical components in the image.

        Returns:
            Tuple of (components, raw_wires, raw_junctions)
            - raw_wires and raw_junctions are always empty (wires come from Pass 2)
        """
        if self.use_yolo:
            components = self._detect_with_yolo(image)
            return components, [], []
        else:
            return await self._detect_with_ollama(image, image_pil)

    def connection_aware_layout(self, components: list, connections: list) -> dict:
        """
        Assigns coordinates based on connection order rather than
        arbitrary grid position. Components connected in series
        appear left to right. Parallel branches go top to bottom.
        """
        positions = {}
        
        # Build adjacency from connections
        adjacency = {c["id"]: [] for c in components}
        for conn in connections:
            from_comp = conn["from"].split(".")[0].replace("node_", "")
            to_comp = conn["to"].split(".")[0].replace("node_", "")
            
            # Only add if they're actual component IDs
            from_ids = [c["id"] for c in components]
            if from_comp in from_ids and to_comp in from_ids:
                if to_comp not in adjacency[from_comp]:
                    adjacency[from_comp].append(to_comp)
        
        # BFS layout: place connected components left to right
        visited = set()
        queue = [components[0]["id"]] if components else []
        col, row = 0, 0
        col_width = 180
        row_height = 160
        
        while queue:
            comp_id = queue.pop(0)
            if comp_id in visited:
                continue
            visited.add(comp_id)
            positions[comp_id] = {
                "x": col * col_width + 80,
                "y": row * row_height + 80
            }
            col += 1
            neighbors = adjacency.get(comp_id, [])
            unvisited = [n for n in neighbors if n not in visited]
            queue = unvisited + queue
            if col > 3:
                col = 0
                row += 1
        
        # Place any unconnected components at the end
        for comp in components:
            if comp["id"] not in positions:
                positions[comp["id"]] = {"x": col * col_width + 80, "y": row * row_height + 80}
                col += 1
        
        return positions

    def extract_json_safely(self, raw_response: str) -> dict:
        """
        Gemini is configured to return application/json, so we can parse directly.
        """
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            # Final fallback: return structured error for debugging
            return {
                "parse_error": True,
                "raw_response": raw_response,
                "components": [],
                "nodes": [],
                "connections": []
            }

    def assign_next_available_pin(self, comp_id: str, pin_usage: dict, max_pins: int = 4) -> str:
        """Helper to track and assign pins."""
        if comp_id not in pin_usage:
            pin_usage[comp_id] = 1
        else:
            pin_usage[comp_id] += 1
        return f"pin{pin_usage[comp_id]}"

    async def analyze_circuit_single_pass(self, image_pil) -> dict:
        print("[STEP 2] Sending to Gemini Vision API...")

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # In google-genai, generation is synchronous or we can use async generation if available,
        # but let's use standard generate_content which might block, or we can use aio.
        # Actually, google-genai has client.aio.models.generate_content for async.
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                image_pil,
                OLLAMA_SINGLE_PASS_PROMPT
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )

        raw_response = response.text
        store_last_parse_result(raw_response)

        safe_raw = raw_response[:300].encode('ascii', 'replace').decode('ascii')
        print(f"[STEP 3] Raw response received: {safe_raw}")

        parsed = self.extract_json_safely(raw_response)
        safe_json = json.dumps(parsed, indent=2).encode('ascii', 'replace').decode('ascii')
        print(f"[STEP 4] JSON extraction result: {safe_json}")

        if parsed.get("parse_error"):
            safe_err = raw_response.encode('ascii', 'replace').decode('ascii')
            print(f"[PARSER ERROR] JSON extraction failed. Raw: {safe_err}")
            return parsed

        # Call auto_repair_circuit
        parsed = auto_repair_circuit(
            parsed.get("components", []),
            parsed.get("nodes", []),
            parsed.get("connections", [])
        )

        # Rest of translation logic stays exactly the same
        translated_components = []
        positions = self.connection_aware_layout(
            parsed.get("components", []),
            parsed.get("connections", [])
        )

        for comp in parsed.get("components", []):
            coords = {
                "x": positions.get(comp["id"], {}).get("x", 100),
                "y": positions.get(comp["id"], {}).get("y", 100),
                "width": 100,
                "height": 80
            }
            translated_components.append(DetectedComponent(
                id=comp["id"],
                type=comp["type"],
                value=comp.get("value", ""),
                bbox=BoundingBox(x=coords["x"], y=coords["y"], w=coords["width"], h=coords["height"]),
                pins=self._generate_default_pins(comp["type"], BoundingBox(x=coords["x"], y=coords["y"], w=coords["width"], h=coords["height"])),
                confidence=1.0,
                source="gemini"
            ))

        pin_usage = {}
        translated_nodes = []

        for node in parsed.get("nodes", []):
            node_pins = []
            for comp_id in node.get("connected_components", []):
                pin = self.assign_next_available_pin(comp_id, pin_usage)
                node_pins.append(f"{comp_id}.{pin}")
            translated_nodes.append({
                "id": node["id"],
                "pins": node_pins
            })

        def validate_circuit_graph(components, nodes, connections):
            comp_ids = {c.id for c in components}
            connected_comps = set()
            
            for node in nodes:
                for comp_id in node.get("connected_components", []):
                    connected_comps.add(comp_id)
            
            orphaned = comp_ids - connected_comps
            if orphaned:
                print(f"[VALIDATION WARNING] These components have no connections: {orphaned}")
            
            print(f"[VALIDATION] {len(components)} components, {len(nodes)} nodes, {len(connections)} connections")
            print(f"[VALIDATION] Connected: {connected_comps}")
            
            return len(orphaned) == 0

        validate_circuit_graph(translated_components, parsed.get('nodes', []), parsed.get('connections', []))

        # Generate Circuit Overview
        components_summary = [
            f"{c.id} ({c.type}): {c.value or 'unknown'}"
            for c in translated_components
        ]
        
        overview_prompt = f"""
This circuit has these components: {components_summary}
Explain in 3 sentences maximum, written for a first-year ECE student:
1. What this circuit does in plain English
2. What the role of each component is
3. What would happen if the resistor/main component was removed
Return only the explanation text, no formatting."""

        try:
            overview_response = await client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=[overview_prompt],
                config=types.GenerateContentConfig(temperature=0.3)
            )
            circuit_overview = overview_response.text
        except Exception as e:
            print(f"[OVERVIEW ERROR] Failed to generate overview: {e}")
            circuit_overview = ""

        return {
            "components": translated_components,
            "nodes": translated_nodes,
            "connections": parsed.get("connections", []),
            "overview": circuit_overview
        }

    def _generate_default_pins(
        self, comp_type: str, bbox: BoundingBox
    ) -> list[Pin]:
        """Generate default pin positions based on component type and bounding box."""
        cx, cy = bbox.center.x, bbox.center.y
        left = bbox.x
        right = bbox.x + bbox.w
        top = bbox.y
        bottom = bbox.y + bbox.h

        pin_count = COMPONENT_PIN_COUNT.get(comp_type, 2)

        if pin_count == 1:
            return [Pin(name="pin1", x=cx, y=top)]
        elif pin_count == 2:
            return [
                Pin(name="pin1", x=left, y=cy),
                Pin(name="pin2", x=right, y=cy),
            ]
        elif pin_count == 3:
            if comp_type in ("transistor_npn", "transistor_pnp"):
                return [
                    Pin(name="base", x=left, y=cy),
                    Pin(name="collector", x=right, y=top + bbox.h * 0.25),
                    Pin(name="emitter", x=right, y=bottom - bbox.h * 0.25),
                ]
            elif comp_type in ("mosfet_n", "mosfet_p"):
                return [
                    Pin(name="gate", x=left, y=cy),
                    Pin(name="drain", x=right, y=top + bbox.h * 0.25),
                    Pin(name="source", x=right, y=bottom - bbox.h * 0.25),
                ]
            elif comp_type == "opamp":
                return [
                    Pin(name="inv", x=left, y=top + bbox.h * 0.3),
                    Pin(name="noninv", x=left, y=bottom - bbox.h * 0.3),
                    Pin(name="out", x=right, y=cy),
                ]
            else:
                return [
                    Pin(name="pin1", x=left, y=cy),
                    Pin(name="pin2", x=right, y=top + bbox.h * 0.3),
                    Pin(name="pin3", x=right, y=bottom - bbox.h * 0.3),
                ]
        elif pin_count == 4:
            return [
                Pin(name="pin1", x=left, y=top + bbox.h * 0.3),
                Pin(name="pin2", x=left, y=bottom - bbox.h * 0.3),
                Pin(name="pin3", x=right, y=top + bbox.h * 0.3),
                Pin(name="pin4", x=right, y=bottom - bbox.h * 0.3),
            ]
        else:
            return [
                Pin(name="pin1", x=left, y=cy),
                Pin(name="pin2", x=right, y=cy),
            ]

    # ============================================================
    # YOLOv8 Detection (Future)
    # ============================================================

    def _load_yolo(self):
        """Load custom-trained YOLOv8 model."""
        try:
            from ultralytics import YOLO
            self._yolo_model = YOLO(str(YOLO_WEIGHTS_PATH))
            logger.info(f"YOLOv8 model loaded from {YOLO_WEIGHTS_PATH}")
        except ImportError:
            logger.error("ultralytics package not installed")
            self.use_yolo = False
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.use_yolo = False

    def _detect_with_yolo(self, image: np.ndarray) -> list[DetectedComponent]:
        """Run YOLOv8 inference on the image."""
        if self._yolo_model is None:
            raise RuntimeError("YOLO model not loaded")

        results = self._yolo_model(image, conf=YOLO_CONFIDENCE_THRESHOLD)
        components = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                bbox = BoundingBox(x=x1, y=y1, w=x2 - x1, h=y2 - y1)
                pins = self._generate_default_pins(class_name, bbox)
                components.append(DetectedComponent(
                    id=f"yolo_{i + 1}",
                    type=class_name,
                    bbox=bbox,
                    pins=pins,
                    confidence=confidence,
                    source="yolo",
                ))

        logger.info(f"YOLOv8 detected {len(components)} components")
        return components

    # ============================================================
    # Utilities
    # ============================================================

    @staticmethod
    def _clean_json_response(text: str) -> str:
        """Strip markdown code fences from LLM response."""
        text = text.strip()
        if text.startswith("```"):
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3].strip()
        return text
