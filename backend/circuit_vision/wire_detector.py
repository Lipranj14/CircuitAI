"""
circuit_vision/wire_detector.py — Wire & Junction Detection

Classical computer vision pipeline for tracing wires in circuit diagrams:
  1. Mask out detected component regions from the binary image
  2. Skeletonize remaining wire pixels (Zhang-Suen thinning)
  3. Detect line segments via Probabilistic Hough Transform
  4. Find junctions (pixels with ≥3 skeleton neighbors)
  5. Find endpoints (pixels with exactly 1 neighbor)
  6. Build wire connectivity graph
"""

import logging
from typing import Optional

import cv2
import numpy as np

from schemas.domain import (
    WireSegment,
    Junction,
    DetectedComponent,
    Point,
    BoundingBox,
)
from .config import MIN_WIRE_LENGTH

logger = logging.getLogger(__name__)


class WireDetector:
    """
    Detects wires, junctions, and endpoints in a binarized
    circuit diagram image using classical CV techniques.
    """

    def __init__(
        self,
        min_wire_length: int = MIN_WIRE_LENGTH,
        hough_threshold: int = 30,
        hough_min_line_length: int = 15,
        hough_max_line_gap: int = 10,
    ):
        self.min_wire_length = min_wire_length
        self.hough_threshold = hough_threshold
        self.hough_min_line_length = hough_min_line_length
        self.hough_max_line_gap = hough_max_line_gap

    # ============================================================
    # Public API
    # ============================================================

    def detect(
        self,
        binary_image: np.ndarray,
        components: Optional[list[DetectedComponent]] = None,
    ) -> tuple[list[WireSegment], list[Junction]]:
        """
        Detect wires and junctions in the binary image.

        Args:
            binary_image: Binarized image (white background, black lines)
            components: Detected components whose regions will be masked out

        Returns:
            Tuple of (wire_segments, junctions)
        """
        # Step 1: Create wire-only image by masking out component regions
        wire_image = self._mask_components(binary_image, components or [])

        # Step 2: Invert so wires are white on black (required for skeletonize)
        wire_inv = cv2.bitwise_not(wire_image)

        # Step 3: Skeletonize to get single-pixel-width wire traces
        skeleton = self._skeletonize(wire_inv)

        # Step 4: Detect line segments using Hough Transform
        wire_segments = self._detect_hough_lines(skeleton)

        # Step 5: Detect junctions and endpoints from skeleton
        junctions = self._detect_junctions(skeleton)

        logger.info(
            f"Wire detection: {len(wire_segments)} segments, "
            f"{len(junctions)} junctions"
        )

        return wire_segments, junctions

    def detect_from_gemini(
        self, raw_wires: list[dict], raw_junctions: list[dict]
    ) -> tuple[list[WireSegment], list[Junction]]:
        """
        Convert Gemini-provided wire/junction data into typed objects.
        Used when the CV wire detection is skipped or as supplementary data.

        Args:
            raw_wires: Wire dicts from Gemini: [{id, start:{x,y}, end:{x,y}}, ...]
            raw_junctions: Junction dicts: [{id, position:{x,y}}, ...]

        Returns:
            Tuple of (wire_segments, junctions)
        """
        wires = []
        for i, w in enumerate(raw_wires):
            wire_id = w.get("id", f"wire_{i + 1}")
            start = w.get("start", {})
            end = w.get("end", {})

            seg = WireSegment(
                id=wire_id,
                start=Point(
                    x=float(start.get("x", 0)),
                    y=float(start.get("y", 0)),
                ),
                end=Point(
                    x=float(end.get("x", 0)),
                    y=float(end.get("y", 0)),
                ),
                wire_type=self._classify_wire_type(
                    float(start.get("x", 0)), float(start.get("y", 0)),
                    float(end.get("x", 0)), float(end.get("y", 0)),
                ),
            )
            wires.append(seg)

        juncs = []
        for i, j in enumerate(raw_junctions):
            junc_id = j.get("id", f"junc_{i + 1}")
            pos = j.get("position", {})
            juncs.append(Junction(
                id=junc_id,
                position=Point(
                    x=float(pos.get("x", 0)),
                    y=float(pos.get("y", 0)),
                ),
            ))

        return wires, juncs

    # ============================================================
    # Pipeline Steps
    # ============================================================

    def _mask_components(
        self,
        binary_image: np.ndarray,
        components: list[DetectedComponent],
    ) -> np.ndarray:
        """
        Mask out detected component regions so only wires remain.

        Fills each component's bounding box with white (background)
        to isolate wire-only pixels.
        """
        masked = binary_image.copy()
        for comp in components:
            bb = comp.bbox
            # Add a small margin around each component
            margin = 5
            x1 = max(0, int(bb.x) - margin)
            y1 = max(0, int(bb.y) - margin)
            x2 = min(masked.shape[1], int(bb.x + bb.w) + margin)
            y2 = min(masked.shape[0], int(bb.y + bb.h) + margin)
            # Fill with white (background color in binary image)
            masked[y1:y2, x1:x2] = 255

        return masked

    def _skeletonize(self, binary_inv: np.ndarray) -> np.ndarray:
        """
        Reduce wire pixels to single-pixel-width skeleton using
        morphological thinning (Zhang-Suen algorithm via OpenCV).

        Input: White wires on black background
        Output: Single-pixel-width skeleton (white on black)
        """
        # Ensure binary
        _, binary = cv2.threshold(binary_inv, 127, 255, cv2.THRESH_BINARY)

        # Use cv2.ximgproc.thinning if available, else manual thinning
        try:
            skeleton = cv2.ximgproc.thinning(
                binary, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN
            )
        except AttributeError:
            # Fallback: manual iterative morphological thinning
            skeleton = self._manual_skeletonize(binary)

        return skeleton

    def _manual_skeletonize(self, binary: np.ndarray) -> np.ndarray:
        """
        Fallback skeletonization using iterative morphological erosion.
        Less precise than Zhang-Suen but works without opencv-contrib.
        """
        skeleton = np.zeros_like(binary)
        element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        temp = binary.copy()

        while True:
            eroded = cv2.erode(temp, element)
            dilated = cv2.dilate(eroded, element)
            diff = cv2.subtract(temp, dilated)
            skeleton = cv2.bitwise_or(skeleton, diff)
            temp = eroded.copy()

            if cv2.countNonZero(temp) == 0:
                break

        return skeleton

    def _detect_hough_lines(self, skeleton: np.ndarray) -> list[WireSegment]:
        """
        Detect line segments in the skeleton image using
        Probabilistic Hough Transform.
        """
        lines = cv2.HoughLinesP(
            skeleton,
            rho=1,
            theta=np.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=self.hough_min_line_length,
            maxLineGap=self.hough_max_line_gap,
        )

        segments = []
        if lines is None:
            return segments

        for i, line in enumerate(lines):
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

            # Filter very short segments (noise)
            if length < self.min_wire_length:
                continue

            wire_type = self._classify_wire_type(x1, y1, x2, y2)

            segments.append(WireSegment(
                id=f"hw_{i + 1}",
                start=Point(x=float(x1), y=float(y1)),
                end=Point(x=float(x2), y=float(y2)),
                wire_type=wire_type,
            ))

        return segments

    def _detect_junctions(self, skeleton: np.ndarray) -> list[Junction]:
        """
        Find junction points in the skeleton image.

        A junction is a skeleton pixel that has 3 or more neighboring
        skeleton pixels in its 3×3 neighborhood.
        """
        # Count neighbors for each pixel using convolution
        # Kernel that counts 8-connected neighbors
        kernel = np.array([
            [1, 1, 1],
            [1, 0, 1],
            [1, 1, 1],
        ], dtype=np.float32)

        # Normalize skeleton to 0/1
        skel_01 = (skeleton > 0).astype(np.float32)

        # Convolve to count neighbors
        neighbor_count = cv2.filter2D(skel_01, -1, kernel)

        # Junctions: skeleton pixels with ≥3 neighbors
        junction_mask = (skel_01 > 0) & (neighbor_count >= 3)

        # Find coordinates of junction pixels
        junction_points = np.argwhere(junction_mask)

        # Cluster nearby junction pixels (within 5px) into single junctions
        junctions = self._cluster_points(junction_points, cluster_radius=5)

        return [
            Junction(
                id=f"j_{i + 1}",
                position=Point(x=float(pt[1]), y=float(pt[0])),  # argwhere gives (row, col)
            )
            for i, pt in enumerate(junctions)
        ]

    # ============================================================
    # Utilities
    # ============================================================

    @staticmethod
    def _classify_wire_type(
        x1: float, y1: float, x2: float, y2: float
    ) -> str:
        """Classify a wire segment as horizontal, vertical, or diagonal."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        if dy < 5:
            return "horizontal"
        elif dx < 5:
            return "vertical"
        else:
            return "diagonal"

    @staticmethod
    def _cluster_points(
        points: np.ndarray, cluster_radius: int = 5
    ) -> list[np.ndarray]:
        """
        Cluster nearby points into centroids.
        Simple greedy clustering: take each unvisited point, collect
        all points within radius, compute centroid, mark as visited.
        """
        if len(points) == 0:
            return []

        visited = np.zeros(len(points), dtype=bool)
        centroids = []

        for i in range(len(points)):
            if visited[i]:
                continue

            # Find all points within radius of point[i]
            dists = np.sqrt(np.sum((points - points[i]) ** 2, axis=1))
            cluster_mask = dists <= cluster_radius
            cluster_mask &= ~visited

            # Mark as visited
            visited[cluster_mask] = True

            # Compute centroid of cluster
            cluster_points = points[cluster_mask]
            centroid = cluster_points.mean(axis=0).astype(int)
            centroids.append(centroid)

        return centroids
