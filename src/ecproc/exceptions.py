"""ecproc exception hierarchy."""

from __future__ import annotations


class EcprocError(Exception):
    """Base exception for all ecproc errors."""


class ParseError(EcprocError):
    """Error during parsing of .ecproc or .py files."""

    def __init__(
        self,
        message: str,
        *,
        line: int | None = None,
        column: int | None = None,
        file: str | None = None,
    ) -> None:
        self.line = line
        self.column = column
        self.file = file
        loc = ""
        if file:
            loc += f"{file}:"
        if line is not None:
            loc += f"{line}:"
        if column is not None:
            loc += f"{column}:"
        if loc:
            message = f"{loc} {message}"
        super().__init__(message)


class ValidationError(EcprocError):
    """Base class for validation errors."""


class SyntaxValidationError(ValidationError):
    """L1: Syntax validation failure."""


class ElectrochemValidationError(ValidationError):
    """L2: Electrochemistry parameter/domain rule violation."""


class SafetyValidationError(ValidationError):
    """L3: Safety constraint violation."""


class HardwareValidationError(ValidationError):
    """L4: Hardware capability violation."""


class CompilationError(EcprocError):
    """Error during IR compilation to target."""


class ExecutionError(EcprocError):
    """Error during procedure execution."""
