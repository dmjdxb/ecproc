"""Chronopotentiometry / Galvanostatic technique."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import StepAST
from ecproc.sdk.techniques.base import BaseTechnique


class Galvanostatic(BaseTechnique):
    """Chronopotentiometry / Galvanostatic.

    Applies a constant current to the working electrode for a
    specified duration and records the potential response.
    """

    technique_name = "galvanostatic"

    def __init__(
        self,
        current: float,
        duration: str,
        *,
        sample: str | None = None,
        cutoff: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **{k: v for k, v in kwargs.items() if k in ("tag", "extract", "vendor_flags")}
        )
        self.current = current
        self.duration = duration
        self.sample = sample
        self.cutoff = cutoff

    def validate_params(self) -> list[str]:
        errors = []
        if not self.duration:
            errors.append("Duration must be specified")
        return errors

    def to_step_ast(self) -> StepAST:
        params: dict[str, Any] = {
            "current": self.current,
            "duration": self.duration,
        }
        if self.sample is not None:
            params["sample"] = self.sample
        if self.cutoff is not None:
            params["cutoff"] = self.cutoff
        return StepAST(
            technique="galvanostatic",
            parameters=params,
            tag=self.tag,
            extract=self.extract,
            vendor_flags=self.vendor_flags,
        )


def galvanostatic(current: float, duration: str, **kwargs: Any) -> Galvanostatic:
    """Convenience constructor for Galvanostatic/CP technique."""
    return Galvanostatic(current, duration, **kwargs)
