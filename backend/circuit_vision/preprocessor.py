"""
circuit_vision/preprocessor.py — Image Preprocessing Pipeline

Prepares raw circuit diagram images for downstream detection:
  1. Resize to standard working resolution
  2. Convert to grayscale
  3. Adaptive thresholding for binarization
  4. Morphological denoising (open/close)
  5. Deskew via Hough-line angle correction
  6. CLAHE contrast enhancement for hand-drawn sketches
"""

import cv2
import numpy as np
from dataclasses import dataclass

from .config import (
    MAX_IMAGE_DIMENSION,
    ADAPTIVE_THRESH_BLOCK_SIZE,
    ADAPTIVE_THRESH_C,
    MORPH_KERNEL_SIZE,
)


@dataclass
class PreprocessedImage:
    """Container for all processed image variants."""
    original: np.ndarray       # Original resized color image (BGR)
    grayscale: np.ndarray      # Grayscale version
    binary: np.ndarray         # Binarized (black components on white background)
    binary_inv: np.ndarray     # Inverted binary (white components on black)
    enhanced: np.ndarray       # CLAHE-enhanced grayscale
    scale_factor: float        # Resize scale factor applied (for coordinate mapping)
    original_width: int        # Width before any processing
    original_height: int       # Height before any processing


class ImagePreprocessor:
    """
    Processes raw circuit diagram images into forms suitable for
    component detection, OCR, and wire tracing.
    """

    def __init__(
        self,
        max_dimension: int = MAX_IMAGE_DIMENSION,
        thresh_block_size: int = ADAPTIVE_THRESH_BLOCK_SIZE,
        thresh_c: int = ADAPTIVE_THRESH_C,
        morph_kernel_size: int = MORPH_KERNEL_SIZE,
    ):
        self.max_dimension = max_dimension
        self.thresh_block_size = thresh_block_size
        self.thresh_c = thresh_c
        self.morph_kernel_size = morph_kernel_size

    def process(self, image: np.ndarray) -> PreprocessedImage:
        """
        Run the full preprocessing pipeline on a raw image.

        Args:
            image: Raw input image as numpy array (BGR format from cv2)

        Returns:
            PreprocessedImage with all processed variants
        """
        original_h, original_w = image.shape[:2]

        # Step 1: Resize to working resolution
        resized, scale_factor = self._resize(image)

        # Step 2: Convert to grayscale
        grayscale = self._to_grayscale(resized)

        # Step 3: Enhance contrast (CLAHE) — especially helps hand-drawn sketches
        enhanced = self._enhance_contrast(grayscale)

        # Step 4: Binarize using adaptive thresholding
        binary = self._binarize(enhanced)

        # Step 5: Denoise with morphological operations
        binary = self._denoise(binary)

        # Step 6: Deskew if the image is rotated
        deskew_angle = self._estimate_skew(binary)
        if abs(deskew_angle) > 0.5:  # Only deskew if angle is significant
            binary = self._rotate(binary, -deskew_angle)
            grayscale = self._rotate(grayscale, -deskew_angle)
            enhanced = self._rotate(enhanced, -deskew_angle)
            resized = self._rotate(resized, -deskew_angle)

        # Inverted binary (useful for some detection algorithms)
        binary_inv = cv2.bitwise_not(binary)

        return PreprocessedImage(
            original=resized,
            grayscale=grayscale,
            binary=binary,
            binary_inv=binary_inv,
            enhanced=enhanced,
            scale_factor=scale_factor,
            original_width=original_w,
            original_height=original_h,
        )

    # --------------------------------------------------------
    # Private Pipeline Steps
    # --------------------------------------------------------

    def _resize(self, image: np.ndarray) -> tuple[np.ndarray, float]:
        """
        Resize image so the longer edge is at most `max_dimension`.
        Returns (resized_image, scale_factor).
        """
        h, w = image.shape[:2]
        if max(h, w) <= self.max_dimension:
            return image.copy(), 1.0

        scale = self.max_dimension / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, scale

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert BGR image to grayscale."""
        if len(image.shape) == 2:
            return image.copy()
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def _enhance_contrast(self, grayscale: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        to improve contrast in poorly-lit or faded hand-drawn sketches.
        """
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(grayscale)

    def _binarize(self, grayscale: np.ndarray) -> np.ndarray:
        """
        Adaptive thresholding produces clean binary output even with
        uneven lighting across the image (common in phone photos).
        """
        binary = cv2.adaptiveThreshold(
            grayscale,
            maxValue=255,
            adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresholdType=cv2.THRESH_BINARY,
            blockSize=self.thresh_block_size,
            C=self.thresh_c,
        )
        return binary

    def _denoise(self, binary: np.ndarray) -> np.ndarray:
        """
        Remove salt-and-pepper noise using morphological open then close.
        Open removes small bright spots; close fills small dark gaps.
        """
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (self.morph_kernel_size, self.morph_kernel_size)
        )
        # Open: erode then dilate — removes small noise specks
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        # Close: dilate then erode — fills small gaps in lines
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)
        return cleaned

    def _estimate_skew(self, binary: np.ndarray) -> float:
        """
        Estimate document skew angle using Hough lines.
        Returns angle in degrees (positive = clockwise rotation).
        """
        # Detect edges
        edges = cv2.Canny(binary, 50, 150, apertureSize=3)

        # Detect lines via Probabilistic Hough Transform
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=100,
            minLineLength=100,
            maxLineGap=10,
        )

        if lines is None or len(lines) == 0:
            return 0.0

        # Collect angles of near-horizontal lines
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Only consider near-horizontal lines (within ±15° of horizontal)
            if abs(angle) < 15:
                angles.append(angle)

        if not angles:
            return 0.0

        # Median angle is more robust than mean against outliers
        return float(np.median(angles))

    def _rotate(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by a given angle (degrees) around its center."""
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, matrix, (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated


def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """
    Convert raw image bytes (e.g. from file upload) to OpenCV numpy array.

    Args:
        image_bytes: Raw image file bytes (JPEG, PNG, etc.)

    Returns:
        BGR numpy array suitable for OpenCV processing

    Raises:
        ValueError: If the bytes cannot be decoded as an image
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode image from bytes. Ensure valid image format.")
    return image
