"""Faraday IR JSON serialization and deserialization."""

from __future__ import annotations

from pathlib import Path

from ecproc.ir.schema import FaradayIR


def to_json(ir: FaradayIR, *, indent: int = 2) -> str:
    """Serialize FaradayIR to JSON string."""
    return ir.model_dump_json(indent=indent)


def from_json(data: str) -> FaradayIR:
    """Deserialize FaradayIR from JSON string."""
    return FaradayIR.model_validate_json(data)


def to_file(ir: FaradayIR, path: Path | str, *, indent: int = 2) -> None:
    """Write FaradayIR to a .ir.json file."""
    p = Path(path)
    p.write_text(to_json(ir, indent=indent), encoding="utf-8")


def from_file(path: Path | str) -> FaradayIR:
    """Read FaradayIR from a .ir.json file."""
    p = Path(path)
    return from_json(p.read_text(encoding="utf-8"))
