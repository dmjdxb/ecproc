"""Phase context manager for procedure definition."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import (
    CheckpointAST,
    LoopAST,
    PhaseAST,
    StepAST,
)


class Loop:
    """Loop builder for SDK usage."""

    def __init__(self, count: int, *, stop_if: str | None = None) -> None:
        self._count = count
        self._stop_if = stop_if
        self._steps: list[StepAST] = []
        self._checkpoint: CheckpointAST | None = None

    def cv(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("cv", kwargs))
        return self

    def eis(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("eis", kwargs))
        return self

    def lsv(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("lsv", kwargs))
        return self

    def ocp(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("ocp", kwargs))
        return self

    def hold(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("hold", kwargs))
        return self

    def galvanostatic(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("galvanostatic", kwargs))
        return self

    def dpv(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("dpv", kwargs))
        return self

    def swv(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("swv", kwargs))
        return self

    def gcd(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("gcd", kwargs))
        return self

    def cc(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("cc", kwargs))
        return self

    def stripping(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("stripping", kwargs))
        return self

    def purge(self, **kwargs: Any) -> Loop:
        self._steps.append(_make_step("purge", kwargs))
        return self

    def to_ast(self) -> LoopAST:
        return LoopAST(
            count=self._count,
            steps=list(self._steps),
            checkpoint=self._checkpoint,
            stop_if=self._stop_if,
        )


class Phase:
    """Phase builder for procedure definition."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._setup: dict[str, Any] | None = None
        self._stabilize: list[str] | None = None
        self._teardown: dict[str, Any] | None = None
        self._steps: list[Any] = []  # StepAST or LoopAST

    def setup(self, **kwargs: Any) -> None:
        self._setup = kwargs

    def stabilize(self, *conditions: str) -> None:
        self._stabilize = list(conditions)

    def teardown(self, **kwargs: Any) -> None:
        self._teardown = kwargs

    # --- Technique methods ---

    def cv(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("cv", kwargs))

    def eis(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("eis", kwargs))

    def lsv(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("lsv", kwargs))

    def ocp(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("ocp", kwargs))

    def hold(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("hold", kwargs))

    def galvanostatic(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("galvanostatic", kwargs))

    def dpv(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("dpv", kwargs))

    def swv(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("swv", kwargs))

    def gcd(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("gcd", kwargs))

    def cc(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("cc", kwargs))

    def stripping(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("stripping", kwargs))

    def purge(self, **kwargs: Any) -> None:
        self._steps.append(_make_step("purge", kwargs))

    # --- Environment helpers ---

    def gas(self, gas_type: str) -> None:
        if self._setup is None:
            self._setup = {}
        self._setup["gas"] = gas_type

    def rotation(self, rpm: int) -> None:
        if self._setup is None:
            self._setup = {}
        self._setup["rotation"] = rpm

    # --- Control flow ---

    def loop(self, count: int, *, stop_if: str | None = None) -> Loop:
        lp = Loop(count, stop_if=stop_if)
        self._steps.append(lp)
        return lp

    def checkpoint(self, label: str) -> None:
        pass  # Checkpoint handled via loop

    # --- Logging & computation ---

    def log(self, message: str) -> None:
        self._steps.append(_make_step("log", {"message": message}))

    def compute(self, name: str, expression: str) -> None:
        self._steps.append(_make_step("compute", {"name": name, "expression": expression}))

    def to_ast(self) -> PhaseAST:
        steps: list[StepAST | LoopAST] = []
        for s in self._steps:
            if isinstance(s, Loop):
                steps.append(s.to_ast())
            else:
                steps.append(s)
        return PhaseAST(
            name=self._name,
            setup=self._setup,
            stabilize=self._stabilize,
            steps=steps,
            teardown=self._teardown,
        )


def _make_step(technique: str, kwargs: dict[str, Any]) -> StepAST:
    """Create a StepAST from technique name and keyword arguments."""
    tag = kwargs.pop("tag", None)
    extract = kwargs.pop("extract", None)
    vendor_flags = kwargs.pop("vendor_flags", None)
    return StepAST(
        technique=technique,
        parameters=kwargs,
        tag=tag,
        extract=extract,
        vendor_flags=vendor_flags,
    )
