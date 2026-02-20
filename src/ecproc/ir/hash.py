"""Deterministic hashing for Faraday IR and source files."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ecproc.parser.ast import ProcedureAST


def compute_ir_hash(ir_data: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of an IR document.

    Excludes the hash field itself and timestamps for determinism.
    Uses canonical JSON: sorted keys, minimal separators.

    Returns:
        Hash string in format "sha256:<64-char-hex>".
    """
    data = {k: v for k, v in ir_data.items() if k not in ("provenance",)}
    # Also exclude created timestamp from metadata for determinism
    if "metadata" in data and isinstance(data["metadata"], dict):
        meta = dict(data["metadata"])
        meta.pop("created", None)
        data["metadata"] = meta

    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def compute_source_hash(ast: ProcedureAST) -> str:
    """Compute hash of the source AST for provenance tracking.

    Returns:
        Hash string in format "sha256:<64-char-hex>".
    """
    # Hash based on the source file content if available
    if ast.source_file and ast.source_file.exists():
        content = ast.source_file.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        return f"sha256:{digest}"

    # Otherwise hash a canonical representation of the AST
    import dataclasses

    def _to_dict(obj: Any) -> Any:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return {k: _to_dict(v) for k, v in dataclasses.asdict(obj).items()
                    if k != "source_location" and k != "source_file"}
        if isinstance(obj, list):
            return [_to_dict(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _to_dict(v) for k, v in obj.items()}
        return obj

    data = _to_dict(ast)
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
