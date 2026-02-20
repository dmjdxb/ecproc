"""Main validation orchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ecproc.validator.electrochemistry import validate_electrochemistry
from ecproc.validator.errors import ValidationResult
from ecproc.validator.hardware import validate_hardware
from ecproc.validator.safety import validate_safety
from ecproc.validator.syntax import validate_syntax

if TYPE_CHECKING:
    from ecproc.ir.schema import FaradayIR


class ValidationEngine:
    """Four-layer validation orchestrator.

    Runs L1 -> L2 -> L3 -> L4 sequentially.
    Stops at first layer with errors. Warnings propagate.
    """

    def validate(
        self,
        ir: FaradayIR,
        *,
        level: int = 2,
        hardware: dict[str, Any] | None = None,
    ) -> ValidationResult:
        result = ValidationResult()

        # L1: Syntax
        l1 = validate_syntax(ir)
        result.merge(l1)
        if l1.errors:
            return result

        if level < 2:
            return result

        # L2: Electrochemistry
        l2 = validate_electrochemistry(ir)
        result.merge(l2)
        if l2.errors:
            return result

        if level < 3:
            return result

        # L3: Safety
        l3 = validate_safety(ir)
        result.merge(l3)
        if l3.errors:
            return result

        if level < 4:
            return result

        # L4: Hardware
        if hardware is not None:
            l4 = validate_hardware(ir, hardware)
            result.merge(l4)

        return result
