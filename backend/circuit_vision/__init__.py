"""
circuit_vision — AI-Powered Circuit Diagram Recognition Pipeline

This package provides a modular pipeline for:
  1. Preprocessing circuit diagram images
  2. Detecting electrical components (via Gemini VLM or YOLOv8)
  3. Recognizing text labels (via PaddleOCR)
  4. Tracing wires and junctions (via OpenCV)
  5. Building a unified circuit graph
  6. Rendering clean SVG schematics

Usage:
    from circuit_vision.graph_builder import CircuitGraphBuilder
    builder = CircuitGraphBuilder()
    result = await builder.process_image(image_bytes)
"""

__version__ = "1.0.0"
