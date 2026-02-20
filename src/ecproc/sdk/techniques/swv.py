"""Square Wave Voltammetry technique."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import StepAST
from ecproc.sdk.techniques.base import BaseTechnique


class SWV(BaseTechnique):
    """Square Wave Voltammetry.

    Applies a square wave modulation superimposed on a staircase
    potential sweep and records the differential current.
    """

    technique_name = "swv"

    def __init__(
        self,
        start: float,
        end: float,
        *,
        frequency: float = 25.0,
        amplitude: float = 25.0,
        step: float = 4.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **{k: v for k, v in kwargs.items() if k in ("tag", "extract", "vendor_flags")}
        )
        self.start = start
        self.end = end
        self.frequency = frequency
        self.amplitude = amplitude
        self.step = step

    def validate_params(self) -> list[str]:
        errors = []
        if self.start == self.end:
            errors.append("Start and end potentials must differ")
        if self.frequency <= 0:
            errors.append("Frequency must be positive")
        if self.amplitude <= 0:
            errors.append("Amplitude must be positive")
        if self.step <= 0:
            errors.append("Step size must be positive")
        return errors

    def to_step_ast(self) -> StepAST:
        return StepAST(
            technique="swv",
            parameters={
                "start": self.start,
                "end": self.end,
                "frequency": self.frequency,
                "amplitude": self.amplitude,
                "step": self.step,
            },
            tag=self.tag,
            extract=self.extract,
            vendor_flags=self.vendor_flags,
        )


def swv(start: float, end: float, **kwargs: Any) -> SWV:
    """Convenience constructor for SWV technique."""
    return SWV(start, end, **kwargs)
