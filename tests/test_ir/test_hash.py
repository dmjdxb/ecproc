"""Tests for ecproc.ir.hash -- deterministic hashing for IR and source."""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from ecproc.ir.hash import compute_ir_hash, compute_source_hash
from ecproc.parser.ast import (
    MetadataAST,
    PhaseAST,
    ProcedureAST,
    StepAST,
    SystemAST,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ir_dict(**overrides) -> dict:
    """Build a minimal IR dict (as would come from model_dump)."""
    now = datetime.now(timezone.utc).isoformat()
    defaults = {
        "faraday_version": "1.0",
        "metadata": {
            "protocol": "test-proto",
            "version": "1.0",
            "created": now,
            "ecproc_version": "0.1.0",
            "source_hash": "sha256:abc",
            "author": None,
        },
        "system": {"electrodes": 3, "reference": "RHE"},
        "procedure": [
            {
                "name": "activation",
                "steps": [
                    {"technique": "cv", "scan_rate": 0.05, "vertex1": 0.05, "vertex2": 1.2},
                ],
            },
        ],
        "safety": None,
        "state_recovery": None,
        "variables": None,
        "output": None,
        "provenance": {
            "source_file": None,
            "source_hash": "sha256:abc",
            "parser_version": "0.1.0",
        },
    }
    defaults.update(overrides)
    return defaults


def _make_ast(**overrides) -> ProcedureAST:
    """Build a minimal ProcedureAST for source hash tests."""
    defaults = dict(
        metadata=MetadataAST(protocol="test", version="1.0"),
        system=SystemAST(electrodes=3, reference="RHE"),
        procedure=[
            PhaseAST(
                name="phase1",
                steps=[StepAST(technique="cv", parameters={"scan_rate": "50 mV/s"})],
            ),
        ],
    )
    defaults.update(overrides)
    return ProcedureAST(**defaults)


# ---------------------------------------------------------------------------
# compute_ir_hash tests
# ---------------------------------------------------------------------------


class TestComputeIRHash:
    """Tests for compute_ir_hash."""

    def test_returns_sha256_prefix(self):
        data = _make_ir_dict()
        h = compute_ir_hash(data)
        assert h.startswith("sha256:")

    def test_hash_is_64_hex_chars(self):
        data = _make_ir_dict()
        h = compute_ir_hash(data)
        hex_part = h[len("sha256:"):]
        assert len(hex_part) == 64
        # Validate hex characters
        int(hex_part, 16)

    def test_deterministic_same_input(self):
        data = _make_ir_dict()
        h1 = compute_ir_hash(data)
        h2 = compute_ir_hash(data)
        assert h1 == h2

    def test_different_input_different_hash(self):
        d1 = _make_ir_dict()
        d2 = _make_ir_dict()
        d2["system"]["electrodes"] = 2
        assert compute_ir_hash(d1) != compute_ir_hash(d2)

    def test_excludes_provenance(self):
        """Changing provenance should not affect hash."""
        d1 = _make_ir_dict()
        d2 = copy.deepcopy(d1)
        d2["provenance"]["source_file"] = "/some/other/file.yaml"
        d2["provenance"]["source_hash"] = "sha256:different"
        assert compute_ir_hash(d1) == compute_ir_hash(d2)

    def test_excludes_created_timestamp(self):
        """Changing created timestamp should not affect hash."""
        d1 = _make_ir_dict()
        d2 = copy.deepcopy(d1)
        d2["metadata"]["created"] = "2099-12-31T23:59:59Z"
        assert compute_ir_hash(d1) == compute_ir_hash(d2)

    def test_protocol_change_changes_hash(self):
        d1 = _make_ir_dict()
        d2 = copy.deepcopy(d1)
        d2["metadata"]["protocol"] = "different-proto"
        assert compute_ir_hash(d1) != compute_ir_hash(d2)

    def test_step_parameter_change_changes_hash(self):
        d1 = _make_ir_dict()
        d2 = copy.deepcopy(d1)
        d2["procedure"][0]["steps"][0]["scan_rate"] = 0.1
        assert compute_ir_hash(d1) != compute_ir_hash(d2)


# ---------------------------------------------------------------------------
# compute_source_hash tests
# ---------------------------------------------------------------------------


class TestComputeSourceHash:
    """Tests for compute_source_hash."""

    def test_returns_sha256_prefix(self):
        ast = _make_ast()
        h = compute_source_hash(ast)
        assert h.startswith("sha256:")

    def test_deterministic(self):
        ast = _make_ast()
        h1 = compute_source_hash(ast)
        h2 = compute_source_hash(ast)
        assert h1 == h2

    def test_different_ast_different_hash(self):
        a1 = _make_ast()
        a2 = _make_ast(
            metadata=MetadataAST(protocol="other", version="2.0"),
        )
        assert compute_source_hash(a1) != compute_source_hash(a2)

    def test_from_source_file(self, tmp_path):
        """When source_file exists, hash is based on file content."""
        f = tmp_path / "test.yaml"
        f.write_text("some yaml content", encoding="utf-8")
        ast = _make_ast()
        ast.source_file = f
        h = compute_source_hash(ast)
        assert h.startswith("sha256:")

    def test_file_content_change_changes_hash(self, tmp_path):
        """Different file content -> different hash."""
        f1 = tmp_path / "v1.yaml"
        f1.write_text("version one", encoding="utf-8")
        f2 = tmp_path / "v2.yaml"
        f2.write_text("version two", encoding="utf-8")

        ast1 = _make_ast()
        ast1.source_file = f1
        ast2 = _make_ast()
        ast2.source_file = f2
        assert compute_source_hash(ast1) != compute_source_hash(ast2)
