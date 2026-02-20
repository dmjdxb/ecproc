"""Abstract base class for compilation targets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompilationResult:
    """Result of compiling IR to a target."""
    target: str
    output: Any
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result of executing a compiled procedure."""
    success: bool
    target: str
    observations: list[dict[str, Any]] = field(default_factory=list)
    data_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started: str = ""
    completed: str = ""
    hardware: str = ""


class ECProcTarget(ABC):
    """Abstract base class for compilation targets."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Target identifier."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Target version string."""
        ...

    @abstractmethod
    def capabilities(self) -> dict[str, Any]:
        """Declare target capabilities."""
        ...

    @abstractmethod
    def compile(self, ir: Any) -> CompilationResult:
        """Compile IR to target format."""
        ...

    @abstractmethod
    def execute(self, compiled: CompilationResult) -> ExecutionResult:
        """Execute a compiled procedure."""
        ...

    def validate_ir(self, ir: Any) -> list[str]:
        """Check if IR is compatible with this target."""
        return []
