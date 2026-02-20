"""Electrochemical Impedance Spectroscopy technique."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import StepAST
from ecproc.sdk.techniques.base import BaseTechnique


class EIS(BaseTechnique):
    """Electrochemical Impedance Spectroscopy.

    Applies a small sinusoidal perturbation across a range of
    frequencies and measures the impedance response.
    """

    technique_name = "eis"

    def __init__(
        self,
        f_start: float,
        f_end: float,
        *,
        amplitude: float = 10.0,
        at: str | float = "OCP",
        ppd: int = 10,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **{k: v for k, v in kwargs.items() if k in ("tag", "extract", "vendor_flags")}
        )
        self.f_start = f_start
        self.f_end = f_end
        self.amplitude = amplitude
        self.at = at
        self.ppd = ppd

    def validate_params(self) -> list[str]:
        errors = []
        if self.f_start <= 0:
            errors.append("Start frequency must be positive")
        if self.f_end <= 0:
            errors.append("End frequency must be positive")
        if self.amplitude <= 0:
            errors.append("Amplitude must be positive")
        if self.ppd <= 0:
            errors.append("Points per decade must be positive")
        return errors

    def to_step_ast(self) -> StepAST:
        return StepAST(
            technique="eis",
            parameters={
                "f_start": self.f_start,
                "f_end": self.f_end,
                "amplitude": self.amplitude,
                "at": self.at,
                "ppd": self.ppd,
            },
            tag=self.tag,
            extract=self.extract,
            vendor_flags=self.vendor_flags,
        )


def eis(f_start: float, f_end: float, **kwargs: Any) -> EIS:
    """Convenience constructor for EIS technique."""
    return EIS(f_start, f_end, **kwargs)
