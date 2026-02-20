"""Stripping Voltammetry technique."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import StepAST
from ecproc.sdk.techniques.base import BaseTechnique


class Stripping(BaseTechnique):
    """Stripping Voltammetry.

    First deposits analyte onto the electrode at a fixed potential,
    then strips it by scanning the potential, measuring the stripping
    current for quantitative analysis.
    """

    technique_name = "stripping"

    def __init__(
        self,
        deposition_potential: float,
        deposition_time: str,
        scan_start: float,
        scan_end: float,
        *,
        rate: float = 50.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **{k: v for k, v in kwargs.items() if k in ("tag", "extract", "vendor_flags")}
        )
        self.deposition_potential = deposition_potential
        self.deposition_time = deposition_time
        self.scan_start = scan_start
        self.scan_end = scan_end
        self.rate = rate

    def validate_params(self) -> list[str]:
        errors = []
        if not self.deposition_time:
            errors.append("Deposition time must be specified")
        if self.scan_start == self.scan_end:
            errors.append("Scan start and end potentials must differ")
        if self.rate <= 0:
            errors.append("Scan rate must be positive")
        return errors

    def to_step_ast(self) -> StepAST:
        return StepAST(
            technique="stripping",
            parameters={
                "deposition_potential": self.deposition_potential,
                "deposition_time": self.deposition_time,
                "scan_start": self.scan_start,
                "scan_end": self.scan_end,
                "rate": self.rate,
            },
            tag=self.tag,
            extract=self.extract,
            vendor_flags=self.vendor_flags,
        )


def stripping(
    deposition_potential: float,
    deposition_time: str,
    scan_start: float,
    scan_end: float,
    **kwargs: Any,
) -> Stripping:
    """Convenience constructor for Stripping technique."""
    return Stripping(deposition_potential, deposition_time, scan_start, scan_end, **kwargs)
