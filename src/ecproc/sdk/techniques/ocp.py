"""Open Circuit Potential technique."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import StepAST
from ecproc.sdk.techniques.base import BaseTechnique


class OCP(BaseTechnique):
    """Open Circuit Potential measurement.

    Measures the equilibrium potential of the working electrode
    with no applied current or potential.
    """

    technique_name = "ocp"

    def __init__(
        self,
        *,
        stable: str | None = None,
        timeout: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **{k: v for k, v in kwargs.items() if k in ("tag", "extract", "vendor_flags")}
        )
        self.stable = stable
        self.timeout = timeout

    def validate_params(self) -> list[str]:
        return []

    def to_step_ast(self) -> StepAST:
        params: dict[str, Any] = {}
        if self.stable:
            params["stable"] = self.stable
        if self.timeout:
            params["timeout"] = self.timeout
        return StepAST(
            technique="ocp",
            parameters=params,
            tag=self.tag,
            extract=self.extract,
            vendor_flags=self.vendor_flags,
        )


def ocp(**kwargs: Any) -> OCP:
    """Convenience constructor for OCP technique."""
    return OCP(**kwargs)
