import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_ml_initialization():
    """Autouse fixture to mock heavy ML and API initializations during tests."""
    with patch('circuit_vision.label_detector.LabelDetector._init_paddle', lambda self: None):
        with patch('circuit_vision.component_detector.ComponentDetector._load_gemini', lambda self: None):
            yield
