"""Base technique abstract class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ecproc.parser.ast import StepAST


class BaseTechnique(ABC):
    """Abstract base class for electrochemical techniques."""

    technique_name: str = ""

    def __init__(
        self,
        *,
        tag: str | None = None,
        extract: Any | None = None,
        vendor_flags: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.tag = tag
        self.extract = extract
        self.vendor_flags = vendor_flags

    @abstractmethod
    def validate_params(self) -> list[str]:
        """Validate technique-specific parameters. Returns list of error messages."""
        ...

    @abstractmethod
    def to_step_ast(self) -> StepAST:
        """Convert to AST step node."""
        ...
