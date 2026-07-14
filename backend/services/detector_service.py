import logging
import cv2
from PIL import Image

from core.logger import timed_execution
from core.exceptions import DetectionError
from schemas.domain import DetectedComponent, WireSegment, Junction, DetectedLabel, BoundingBox, Pin, Point
from circuit_vision.preprocessor import ImagePreprocessor, load_image_from_bytes
from circuit_vision.component_detector import ComponentDetector
from circuit_vision.label_detector import LabelDetector
from circuit_vision.config import LABEL_ASSOCIATION_MAX_DISTANCE
from google.api_core.exceptions import ResourceExhausted
from core.config import settings

import os

logger = logging.getLogger(__name__)

def gemini_api_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))

class DetectorService:
    """Service responsible for the 3-pass circuit detection pipeline."""
    
    def __init__(self, use_yolo: bool = False, use_paddle_ocr: bool = True):
        self.preprocessor = ImagePreprocessor()
        self.component_detector = ComponentDetector(use_yolo=use_yolo)
        self.label_detector = LabelDetector(use_paddle=use_paddle_ocr)

    @timed_execution("detection")
    async def detect_from_image(self, image_bytes: bytes) -> dict:
        """
        Single-pass detection pipeline.
        Calls LLaVA once, parses JSON, builds circuit graph.
        PaddleOCR bypassed — component values read directly 
        from LLaVA JSON response.
        """
        if not gemini_api_configured():
            return {
                "success": False,
                "error": "Gemini API key not configured.",
                "fix": "Add GEMINI_API_KEY to your .env file."
            }
            
        try:
            # Preprocess
            raw_image = load_image_from_bytes(image_bytes)
            preprocessed = self.preprocessor.process(raw_image)
            img_h, img_w = preprocessed.original.shape[:2]

            # Convert to PIL for Ollama
            rgb = cv2.cvtColor(preprocessed.original, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb)

            result = await self.component_detector.analyze_circuit_single_pass(pil_image)
            
            if result.get("parse_error") or not result.get("components"):
                return {
                    "success": False,
                    "error": result.get("error_reason", "Circuit parsing failed — Vision API returned invalid JSON or empty result")
                }

            components = result["components"]
            netlist_nodes = result["nodes"]
            
            # Assign electrical IDs (V1, R1, etc.)
            components, id_map = self._assign_electrical_ids(components)
            
            # Update node references to match new IDs
            for node in netlist_nodes:
                new_pins = []
                for pin_ref in node.get("pins", []):
                    if "." in pin_ref:
                        c_id, p_name = pin_ref.split(".", 1)
                        if c_id in id_map:
                            new_pins.append(f"{id_map[c_id]}.{p_name}")
                        else:
                            new_pins.append(pin_ref)
                    else:
                        new_pins.append(pin_ref)
                node["pins"] = new_pins
            
            # Build circuit graph from parsed result
            # Using GraphBuilderService to keep consistency
            from services.graph_service import GraphBuilderService
            graph_builder = GraphBuilderService()
            graph = graph_builder.build_graph(
                components=components,
                netlist_nodes=netlist_nodes,
                labels=[],
                img_w=img_w,
                img_h=img_h
            )
            
            safe_graph = str(graph).encode('ascii', 'replace').decode('ascii')
            print("[STEP 5] Graph build result:", safe_graph)
            
            return {
                "success": True,
                "components": components,
                "nodes": netlist_nodes,
                "connections": [], # Connections are implicitly in the graph
                "graph": graph,
                "overview": result.get("overview", ""),
                "fallback": False
            }
            
        except Exception as e:
            err_str = str(e).lower()
            if "connection error" in err_str or "connect call failed" in err_str or "connection refused" in err_str:
                raise DetectionError("Ollama is not running or unreachable at localhost:11434. Please start it and ensure the llava model is pulled.", original_error=e)
            raise DetectionError(f"Failed to detect circuit elements: {str(e)}", original_error=e)

    @staticmethod
    def _assign_electrical_ids(components: list[DetectedComponent]) -> tuple[list[DetectedComponent], dict]:
        """Assign standard electrical IDs like V1, R1, D1, etc. Returns updated components and id mapping."""
        counts = {}
        id_map = {}
        prefix_map = {
            "resistor": "R", "battery": "V", "voltage_source": "V", "dc_source": "V",
            "current_source": "I", "capacitor": "C", "inductor": "L", "diode": "D",
            "led": "D", "switch": "SW", "opamp": "OP", "ground": "GND",
            "transistor_npn": "Q", "transistor_pnp": "Q", "mosfet_n": "M", "mosfet_p": "M",
        }
        for comp in components:
            ctype = comp.type.lower()
            prefix = prefix_map.get(ctype, "U")
            old_id = comp.id
            
            if ctype == "ground":
                counts[prefix] = counts.get(prefix, 0) + 1
                comp.id = f"{prefix}{counts[prefix]}"
                if not comp.label:
                    comp.label = "GND"
            else:
                counts[prefix] = counts.get(prefix, 0) + 1
                comp.id = f"{prefix}{counts[prefix]}"
                if not comp.label:
                    comp.label = comp.id
                    
            id_map[old_id] = comp.id
            
        return components, id_map

