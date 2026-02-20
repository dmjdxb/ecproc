"""ecproc - Domain-specific language for electrochemical procedures."""

from ecproc._version import __version__
from ecproc.exceptions import (
    CompilationError,
    EcprocError,
    ElectrochemValidationError,
    ExecutionError,
    HardwareValidationError,
    ParseError,
    SafetyValidationError,
    SyntaxValidationError,
    ValidationError,
)
from ecproc.sdk.procedure import Procedure

__all__ = [
    "__version__",
    "Procedure",
    "EcprocError",
    "ParseError",
    "ValidationError",
    "SyntaxValidationError",
    "ElectrochemValidationError",
    "SafetyValidationError",
    "HardwareValidationError",
    "CompilationError",
    "ExecutionError",
]
