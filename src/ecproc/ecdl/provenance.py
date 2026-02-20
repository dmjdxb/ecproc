"""IR hash linking and chain of custody."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ecproc.ir.hash import compute_ir_hash

if TYPE_CHECKING:
    from ecproc.ir.schema import FaradayIR


def verify_provenance(ir: FaradayIR, expected_hash: str) -> bool:
    """Verify that an IR document matches an expected hash."""
    ir_data = ir.model_dump()
    actual_hash = compute_ir_hash(ir_data)
    return actual_hash == expected_hash


def create_provenance_chain(
    source_file: str | None,
    ir: FaradayIR,
) -> dict[str, str]:
    """Create a provenance chain from source to IR."""
    ir_data = ir.model_dump()
    return {
        "source_file": source_file or "",
        "source_hash": ir.provenance.source_hash,
        "ir_hash": compute_ir_hash(ir_data),
        "parser_version": ir.provenance.parser_version,
    }
