"""
circuit_vision/label_detector.py — OCR-based Text/Label Detection

Detects and recognizes text labels in circuit diagrams using PaddleOCR.
Handles engineering notation: R1, C2, 1kΩ, 10μF, VCC, GND, LM741, etc.

Falls back to a simpler regex-based extraction from Gemini results
if PaddleOCR is not installed.
"""

import logging
import math
import re
from typing import Optional

import numpy as np

from schemas.domain import DetectedLabel, DetectedComponent, BoundingBox, Point
from .config import (
    OCR_CONFIDENCE_THRESHOLD,
    LABEL_ASSOCIATION_MAX_DISTANCE,
)

logger = logging.getLogger(__name__)

# Regex pattern matching common circuit labels
# Matches: R1, R2, C1, L1, D1, LED1, Q1, OP1, U1, SW1, T1, M1
# Also: VCC, VDD, GND, Vin, Vout, V+, V-, 1kΩ, 10μF, 2N2222, LM741
CIRCUIT_LABEL_PATTERN = re.compile(
    r'^('
    r'[RCLQDMSUT]\d*'           # Component designators: R1, C2, L1, etc.
    r'|LED\d*'                   # LED1, LED2
    r'|OP\d*'                    # OP1, OP2
    r'|IC\d*'                    # IC1
    r'|SW\d*'                    # SW1
    r'|V(in|out|cc|dd|ss|ee)'   # Power/signal labels
    r'|GND|VCC|VDD|VSS|VEE'    # Power rails
    r'|U_?[A-Z]?'               # Generic IC designators
    r'|\d+[kKmMuμµnpGT]?[ΩΩFHVAWHz]*'  # Values: 1k, 10uF, 220, 9V
    r'|[A-Z]{2,}\d*'            # Generic 2+ letter codes
    r'|2N\d+'                    # Transistor part numbers
    r'|LM\d+'                   # IC part numbers
    r'|BC\d+'                    # Transistor part numbers
    r'|[+-]'                     # Polarity marks
    r')$',
    re.IGNORECASE
)


class LabelDetector:
    """
    Detects text labels in circuit diagrams and associates them
    with the nearest detected component.
    """

    def __init__(self, use_paddle: bool = True):
        """
        Args:
            use_paddle: If True, attempt to use PaddleOCR. Falls back
                        to Gemini-provided labels if unavailable.
        """
        self._paddle_ocr = None
        self._paddle_available = False

        if use_paddle:
            self._init_paddle()

    # ============================================================
    # Public API
    # ============================================================

    def detect_labels(
        self,
        image: np.ndarray,
        existing_components: Optional[list[DetectedComponent]] = None,
    ) -> list[DetectedLabel]:
        """
        Detect all text labels in the image using OCR.

        Args:
            image: Preprocessed grayscale or color image
            existing_components: Already-detected components (to mask regions)

        Returns:
            List of DetectedLabel objects with text and positions
        """
        if self._paddle_available:
            return self._detect_with_paddle(image)
        else:
            logger.info("PaddleOCR not available — using component labels from detector")
            return self._extract_labels_from_components(existing_components or [])

    def associate_labels_with_components(
        self,
        labels: list[DetectedLabel],
        components: list[DetectedComponent],
        max_distance: float = LABEL_ASSOCIATION_MAX_DISTANCE,
    ) -> list[DetectedLabel]:
        """
        Associate each OCR-detected label with its nearest component.

        Uses Euclidean distance between label center and component
        bounding box center. A label is associated only if the nearest
        component is within `max_distance` pixels.

        Args:
            labels: Detected labels from OCR
            components: Detected components
            max_distance: Maximum pixel distance for association

        Returns:
            Labels with updated `associated_component_id` fields
        """
        for label in labels:
            min_dist = float("inf")
            best_comp_id = None

            for comp in components:
                dist = self._distance(label.position, comp.bbox.center)
                if dist < min_dist:
                    min_dist = dist
                    best_comp_id = comp.id

            if min_dist <= max_distance and best_comp_id is not None:
                label.associated_component_id = best_comp_id

        return labels

    # ============================================================
    # PaddleOCR Detection
    # ============================================================

    def _init_paddle(self):
        """Attempt to initialize PaddleOCR."""
        try:
            from paddleocr import PaddleOCR
            # use_angle_cls=True enables text direction classification
            # lang='en' for English text (component labels)
            self._paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang='en',
                show_log=False,
                use_gpu=False,
            )
            self._paddle_available = True
            logger.info("PaddleOCR initialized successfully")
        except ImportError:
            logger.warning(
                "PaddleOCR not installed. Install with: "
                "pip install paddlepaddle paddleocr"
            )
            self._paddle_available = False
        except Exception as e:
            logger.warning(f"PaddleOCR init failed: {e}")
            self._paddle_available = False

    def _detect_with_paddle(self, image: np.ndarray) -> list[DetectedLabel]:
        """
        Run PaddleOCR on the image and filter results for circuit labels.

        PaddleOCR returns results in format:
        [
            [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], (text, confidence)],
            ...
        ]
        """
        if self._paddle_ocr is None:
            return []

        results = self._paddle_ocr.ocr(image, cls=True)
        labels = []

        if not results or results[0] is None:
            return labels

        for idx, line in enumerate(results[0]):
            if line is None or len(line) < 2:
                continue

            box_points = line[0]      # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text_info = line[1]       # (text, confidence)
            text = text_info[0].strip()
            confidence = float(text_info[1])

            # Filter by confidence threshold
            if confidence < OCR_CONFIDENCE_THRESHOLD:
                continue

            # Filter: only keep strings that look like circuit labels
            if not self._is_circuit_label(text):
                continue

            # Compute bounding box from the 4 corner points
            xs = [p[0] for p in box_points]
            ys = [p[1] for p in box_points]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)

            bbox = BoundingBox(
                x=x_min, y=y_min,
                w=x_max - x_min, h=y_max - y_min,
            )

            labels.append(DetectedLabel(
                text=text,
                position=bbox.center,
                bbox=bbox,
                confidence=confidence,
            ))

        logger.info(f"PaddleOCR detected {len(labels)} circuit labels")
        return labels

    # ============================================================
    # Fallback: Extract labels from Gemini-detected components
    # ============================================================

    def _extract_labels_from_components(
        self, components: list[DetectedComponent]
    ) -> list[DetectedLabel]:
        """
        When OCR is unavailable, create label objects from the
        labels already provided by the component detector (Gemini).
        """
        labels = []
        for comp in components:
            if comp.label:
                labels.append(DetectedLabel(
                    text=comp.label,
                    position=comp.bbox.center,
                    bbox=comp.bbox,
                    confidence=comp.confidence,
                    associated_component_id=comp.id,
                ))
            if comp.value:
                # Add value as a separate label slightly below the component
                val_position = Point(
                    x=comp.bbox.center.x,
                    y=comp.bbox.y + comp.bbox.h + 10,
                )
                labels.append(DetectedLabel(
                    text=comp.value,
                    position=val_position,
                    bbox=BoundingBox(
                        x=comp.bbox.x, y=val_position.y,
                        w=comp.bbox.w, h=15,
                    ),
                    confidence=comp.confidence,
                    associated_component_id=comp.id,
                ))
        return labels

    # ============================================================
    # Utilities
    # ============================================================

    @staticmethod
    def _is_circuit_label(text: str) -> bool:
        """
        Check if a text string looks like a valid circuit label.
        Filters out noise, stray marks, and non-label text.
        """
        # Too short or too long — unlikely to be a label
        if len(text) < 1 or len(text) > 20:
            return False

        # Match against known circuit label patterns
        if CIRCUIT_LABEL_PATTERN.match(text):
            return True

        # Also accept purely numeric values (resistor values etc.)
        if text.replace(".", "").replace(",", "").isdigit():
            return True

        return False

    @staticmethod
    def _distance(p1: Point, p2: Point) -> float:
        """Euclidean distance between two points."""
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)
