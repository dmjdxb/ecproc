"""Four-layer validation engine.

Layers:
    L1 - Syntax: structural checks on IR
    L2 - Electrochemistry: parameter-value and domain-rule checks
    L3 - Safety: equipment and personnel protection
    L4 - Hardware: potentiostat capability checks
"""

from ecproc.validator.electrochemistry import get_registry, validate_electrochemistry
from ecproc.validator.engine import ValidationEngine
from ecproc.validator.errors import Severity, ValidationIssue, ValidationResult
from ecproc.validator.hardware import validate_hardware
from ecproc.validator.safety import validate_safety
from ecproc.validator.syntax import validate_syntax

__all__ = [
    "ValidationEngine",
    "ValidationResult",
    "ValidationIssue",
    "Severity",
    "validate_syntax",
    "validate_electrochemistry",
    "validate_safety",
    "validate_hardware",
    "get_registry",
]
