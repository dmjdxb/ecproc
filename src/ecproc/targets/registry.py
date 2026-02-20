"""Plugin registration and discovery for targets."""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ecproc.targets.base import ECProcTarget


class TargetRegistry:
    """Registry for compilation targets with plugin discovery."""

    def __init__(self) -> None:
        self._targets: dict[str, ECProcTarget] = {}

    def register(self, target: ECProcTarget) -> None:
        """Register a target."""
        self._targets[target.name] = target

    def get(self, name: str) -> ECProcTarget | None:
        """Get a registered target by name."""
        return self._targets.get(name)

    def list_targets(self) -> list[str]:
        """List registered target names."""
        return list(self._targets.keys())

    def discover(self) -> None:
        """Discover and register plugins via entry points."""
        try:
            eps = importlib.metadata.entry_points()
            group: list[Any] = list(eps.get("ecproc.targets", []))
            if hasattr(eps, "select"):
                group = eps.select(group="ecproc.targets")
            for ep in group:
                try:
                    target_cls = ep.load()
                    target = target_cls()
                    self.register(target)
                except Exception:
                    pass
        except Exception:
            pass


# Global registry
_registry = TargetRegistry()


def get_registry() -> TargetRegistry:
    """Get the global target registry."""
    return _registry
