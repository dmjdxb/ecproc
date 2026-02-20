"""ECDL JSON serialization."""

from __future__ import annotations

from pathlib import Path

from ecproc.ecdl.schema import ECDLDocument


def to_json(doc: ECDLDocument, *, indent: int = 2) -> str:
    return doc.model_dump_json(indent=indent)


def from_json(data: str) -> ECDLDocument:
    return ECDLDocument.model_validate_json(data)


def to_file(doc: ECDLDocument, path: Path | str, *, indent: int = 2) -> None:
    Path(path).write_text(to_json(doc, indent=indent), encoding="utf-8")


def from_file(path: Path | str) -> ECDLDocument:
    return from_json(Path(path).read_text(encoding="utf-8"))
