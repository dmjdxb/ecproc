"""Trigger functions for checkpoints."""

from __future__ import annotations

from typing import Any

from ecproc.parser.ast import TriggerAST


class Trigger:
    """Represents a condition that can fire a checkpoint action."""

    def __init__(
        self,
        type: str,
        value: int | float | str,
        unit: str | None = None,
    ) -> None:
        self.type = type
        self.value = value
        self.unit = unit

    def to_ast(self) -> TriggerAST:
        return TriggerAST(type=self.type, value=self.value, unit=self.unit)


def every(interval: int | float | str, unit: str = "cycles") -> Trigger:
    """Create a periodic trigger.

    Args:
        interval: How often the trigger fires.
        unit: Either "cycles" or a time unit like "min", "s".
    """
    if unit == "cycles":
        return Trigger("every_cycles", int(interval), "cycles")
    return Trigger("every_time", interval, unit)


def when(condition: str) -> Trigger:
    """Create a conditional trigger.

    Args:
        condition: Expression that evaluates to true/false.
    """
    return Trigger("when", condition)


def any_of(*triggers: Trigger) -> dict[str, Any]:
    """Combine triggers with OR logic (fire when any trigger matches)."""
    return {"triggers": [t.to_ast() for t in triggers], "logic": "any"}


def all_of(*triggers: Trigger) -> dict[str, Any]:
    """Combine triggers with AND logic (fire when all triggers match)."""
    return {"triggers": [t.to_ast() for t in triggers], "logic": "all"}
