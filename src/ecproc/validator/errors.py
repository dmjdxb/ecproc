"""Validation result types and issue definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation finding."""
    level: str  # "L1", "L2", "L3", "L4"
    severity: Severity
    code: str  # e.g., "PV001", "DR001", "SF001"
    message: str
    path: str | None = None  # JSON path like "procedure[0].steps[2].rate"
    source_line: int | None = None
    expected: Any | None = None
    actual: Any | None = None


@dataclass
class ValidationResult:
    """Aggregate validation result."""
    valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    def add_error(
        self, level: str, code: str, message: str, **kwargs: Any
    ) -> None:
        self.issues.append(
            ValidationIssue(
                level=level, severity=Severity.ERROR, code=code, message=message, **kwargs
            )
        )
        self.valid = False

    def add_warning(
        self, level: str, code: str, message: str, **kwargs: Any
    ) -> None:
        self.issues.append(
            ValidationIssue(
                level=level, severity=Severity.WARNING, code=code, message=message, **kwargs
            )
        )

    def add_info(
        self, level: str, code: str, message: str, **kwargs: Any
    ) -> None:
        self.issues.append(
            ValidationIssue(
                level=level, severity=Severity.INFO, code=code, message=message, **kwargs
            )
        )

    def merge(self, other: ValidationResult) -> None:
        self.issues.extend(other.issues)
        if not other.valid:
            self.valid = False
