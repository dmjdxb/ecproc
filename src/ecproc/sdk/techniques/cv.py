"""Cyclic Voltammetry technique."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import StepAST
from ecproc.sdk.techniques.base import BaseTechnique


class CV(BaseTechnique):
    """Cyclic Voltammetry.

    Sweeps the potential between two vertex potentials at a
    constant scan rate for a specified number of cycles.
    """

    technique_name = "cv"

    def __init__(
        self,
        vertex1: float,
        vertex2: float,
        *,
        rate: float = 50.0,
        cycles: int = 1,
        start: str = "negative",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **{k: v for k, v in kwargs.items() if k in ("tag", "extract", "vendor_flags")}
        )
        self.vertex1 = vertex1
        self.vertex2 = vertex2
        self.rate = rate
        self.cycles = cycles
        self.start = start

    def validate_params(self) -> list[str]:
        errors = []
        if self.rate <= 0:
            errors.append("Scan rate must be positive")
        if self.cycles <= 0:
            errors.append("Cycle count must be positive")
        if self.vertex1 == self.vertex2:
            errors.append("Vertex potentials must differ")
        return errors

    def to_step_ast(self) -> StepAST:
        return StepAST(
            technique="cv",
            parameters={
                "vertex1": self.vertex1,
                "vertex2": self.vertex2,
                "rate": self.rate,
                "cycles": self.cycles,
                "start": self.start,
            },
            tag=self.tag,
            extract=self.extract,
            vendor_flags=self.vendor_flags,
        )


def cv(vertex1: float, vertex2: float, **kwargs: Any) -> CV:
    """Convenience constructor for CV technique."""
    return CV(vertex1, vertex2, **kwargs)
