"""Galvanostatic Charge-Discharge technique."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import StepAST
from ecproc.sdk.techniques.base import BaseTechnique


class GCD(BaseTechnique):
    """Galvanostatic Charge-Discharge.

    Applies constant current charge and discharge cycles,
    typically used for battery and supercapacitor testing.
    """

    technique_name = "gcd"

    def __init__(
        self,
        current: float,
        *,
        voltage_limits: list[float] | None = None,
        cycles: int = 1,
        rest_between: float = 0.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **{k: v for k, v in kwargs.items() if k in ("tag", "extract", "vendor_flags")}
        )
        self.current = current
        self.voltage_limits = voltage_limits
        self.cycles = cycles
        self.rest_between = rest_between

    def validate_params(self) -> list[str]:
        errors = []
        if self.current == 0:
            errors.append("Current must be non-zero")
        if self.cycles <= 0:
            errors.append("Cycle count must be positive")
        if self.rest_between < 0:
            errors.append("Rest time must be non-negative")
        if self.voltage_limits is not None and len(self.voltage_limits) != 2:
            errors.append("Voltage limits must be a pair [low, high]")
        return errors

    def to_step_ast(self) -> StepAST:
        params: dict[str, Any] = {
            "current": self.current,
            "cycles": self.cycles,
            "rest_between": self.rest_between,
        }
        if self.voltage_limits is not None:
            params["voltage_limits"] = self.voltage_limits
        return StepAST(
            technique="gcd",
            parameters=params,
            tag=self.tag,
            extract=self.extract,
            vendor_flags=self.vendor_flags,
        )


def gcd(current: float, **kwargs: Any) -> GCD:
    """Convenience constructor for GCD technique."""
    return GCD(current, **kwargs)
