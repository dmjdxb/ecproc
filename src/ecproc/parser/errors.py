"""Parse error types with source location tracking."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ecproc.exceptions import ParseError

if TYPE_CHECKING:
    from ecproc.parser.ast import SourceLocation


class YAMLStructureError(ParseError):
    """Invalid YAML structure in .ecproc file."""

    def __init__(self, message: str, *, location: SourceLocation | None = None) -> None:
        self.location = location
        super().__init__(
            message,
            line=location.line if location else None,
            column=location.column if location else None,
            file=location.file if location else None,
        )


class MissingFieldError(ParseError):
    """Required field missing from .ecproc file."""

    def __init__(
        self, field: str, section: str, *, location: SourceLocation | None = None
    ) -> None:
        self.field = field
        self.section = section
        self.location = location
        super().__init__(
            f"Missing required field '{field}' in section '{section}'",
            line=location.line if location else None,
            column=location.column if location else None,
            file=location.file if location else None,
        )


class UnknownTechniqueError(ParseError):
    """Unknown electrochemical technique."""

    def __init__(self, technique: str, *, location: SourceLocation | None = None) -> None:
        self.technique = technique
        self.location = location
        super().__init__(
            f"Unknown technique: '{technique}'",
            line=location.line if location else None,
            column=location.column if location else None,
            file=location.file if location else None,
        )


class InvalidSyntaxError(ParseError):
    """Invalid syntax in .ecproc value."""

    def __init__(self, detail: str, *, location: SourceLocation | None = None) -> None:
        self.detail = detail
        self.location = location
        super().__init__(
            f"Invalid syntax: {detail}",
            line=location.line if location else None,
            column=location.column if location else None,
            file=location.file if location else None,
        )
