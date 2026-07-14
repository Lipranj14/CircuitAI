class CircuitException(Exception):
    """Base exception for all domain logic."""
    pass

class PipelineStageError(CircuitException):
    """Raised when a specific pipeline stage fails."""
    def __init__(self, stage: str, message: str, original_error: Exception = None):
        super().__init__(message)
        self.stage = stage
        self.message = message
        self.original_error = original_error

class DetectionError(PipelineStageError):
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__("detection", message, original_error)

class ReconstructionError(PipelineStageError):
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__("reconstruction", message, original_error)

class ValidationError(PipelineStageError):
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__("validation", message, original_error)

class SimulationError(PipelineStageError):
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__("simulation", message, original_error)
