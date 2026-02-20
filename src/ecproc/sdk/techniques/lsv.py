"""Linear Sweep Voltammetry technique."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import StepAST
from ecproc.sdk.techniques.base import BaseTechnique


class LSV(BaseTechnique):
    """Linear Sweep Voltammetry.

    Sweeps the potential linearly from a start potential to an
    end potential at a constant scan rate.
    """

    technique_name = "lsv"

    def __init__(
        self,
        start: float,
        end: float,
        *,
        rate: float = 50.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **{k: v for k, v in kwargs.items() if k in ("tag", "extract", "vendor_flags")}
        )
        self.start = start
        self.end = end
        self.rate = rate

    def validate_params(self) -> list[str]:
        errors = []
        if self.rate <= 0:
            errors.append("Scan rate must be positive")
        if self.start == self.end:
            errors.append("Start and end potentials must differ")
        return errors

    def to_step_ast(self) -> StepAST:
        return StepAST(
            technique="lsv",
            parameters={
                "start": self.start,
                "end": self.end,
                "rate": self.rate,
            },
            tag=self.tag,
            extract=self.extract,
            vendor_flags=self.vendor_flags,
        )


def lsv(start: float, end: float, **kwargs: Any) -> LSV:
    """Convenience constructor for LSV technique."""
    return LSV(start, end, **kwargs)
