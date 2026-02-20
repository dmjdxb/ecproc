"""Differential Pulse Voltammetry technique."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import StepAST
from ecproc.sdk.techniques.base import BaseTechnique


class DPV(BaseTechnique):
    """Differential Pulse Voltammetry.

    Applies a series of potential pulses superimposed on a
    linear potential ramp and records the differential current.
    """

    technique_name = "dpv"

    def __init__(
        self,
        start: float,
        end: float,
        *,
        step: float = 5.0,
        pulse_height: float = 50.0,
        pulse_width: float = 50.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **{k: v for k, v in kwargs.items() if k in ("tag", "extract", "vendor_flags")}
        )
        self.start = start
        self.end = end
        self.step = step
        self.pulse_height = pulse_height
        self.pulse_width = pulse_width

    def validate_params(self) -> list[str]:
        errors = []
        if self.start == self.end:
            errors.append("Start and end potentials must differ")
        if self.step <= 0:
            errors.append("Step size must be positive")
        if self.pulse_height <= 0:
            errors.append("Pulse height must be positive")
        if self.pulse_width <= 0:
            errors.append("Pulse width must be positive")
        return errors

    def to_step_ast(self) -> StepAST:
        return StepAST(
            technique="dpv",
            parameters={
                "start": self.start,
                "end": self.end,
                "step": self.step,
                "pulse_height": self.pulse_height,
                "pulse_width": self.pulse_width,
            },
            tag=self.tag,
            extract=self.extract,
            vendor_flags=self.vendor_flags,
        )


def dpv(start: float, end: float, **kwargs: Any) -> DPV:
    """Convenience constructor for DPV technique."""
    return DPV(start, end, **kwargs)
