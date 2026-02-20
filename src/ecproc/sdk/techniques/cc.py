"""Constant Current / Coulometry technique."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import StepAST
from ecproc.sdk.techniques.base import BaseTechnique


class CC(BaseTechnique):
    """Constant Current / Coulometry.

    Applies a constant potential and measures the accumulated
    charge over a specified duration.
    """

    technique_name = "cc"

    def __init__(
        self,
        potential: float,
        duration: str,
        *,
        sample: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **{k: v for k, v in kwargs.items() if k in ("tag", "extract", "vendor_flags")}
        )
        self.potential = potential
        self.duration = duration
        self.sample = sample

    def validate_params(self) -> list[str]:
        errors = []
        if not self.duration:
            errors.append("Duration must be specified")
        return errors

    def to_step_ast(self) -> StepAST:
        params: dict[str, Any] = {
            "potential": self.potential,
            "duration": self.duration,
        }
        if self.sample is not None:
            params["sample"] = self.sample
        return StepAST(
            technique="cc",
            parameters=params,
            tag=self.tag,
            extract=self.extract,
            vendor_flags=self.vendor_flags,
        )


def cc(potential: float, duration: str, **kwargs: Any) -> CC:
    """Convenience constructor for CC technique."""
    return CC(potential, duration, **kwargs)
