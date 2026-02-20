"""Tests for ecproc.ir.serializer -- JSON serialization round-trips."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

from ecproc.ir.schema import (
    FaradayIR,
    IRElectrolyte,
    IRMetadata,
    IRPhase,
    IRProvenance,
    IRSafety,
    IRStep,
    IRSystem,
    IRVariables,
    IRWorkingElectrode,
)
from ecproc.ir.serializer import from_file, from_json, to_file, to_json

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_ir(**overrides) -> FaradayIR:
    """Build a minimal valid FaradayIR for serialization tests."""
    now = datetime.now(timezone.utc)
    defaults = dict(
        metadata=IRMetadata(
            protocol="test-proto",
            version="1.0",
            created=now,
            ecproc_version="0.1.0",
            source_hash="sha256:abc123",
            author="tester",
        ),
        system=IRSystem(electrodes=3, reference="RHE"),
        procedure=[
            IRPhase(
                name="activation",
                steps=[
                    IRStep(technique="cv", scan_rate=0.05, vertex1=0.05, vertex2=1.2, cycles=3),
                ],
            ),
        ],
        provenance=IRProvenance(
            source_file=None,
            source_hash="sha256:abc123",
            parser_version="0.1.0",
        ),
    )
    defaults.update(overrides)
    return FaradayIR(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestToJson:
    """to_json produces valid JSON."""

    def test_returns_string(self):
        ir = _make_minimal_ir()
        result = to_json(ir)
        assert isinstance(result, str)

    def test_valid_json(self):
        ir = _make_minimal_ir()
        result = to_json(ir)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_contains_metadata(self):
        ir = _make_minimal_ir()
        parsed = json.loads(to_json(ir))
        assert "metadata" in parsed
        assert parsed["metadata"]["protocol"] == "test-proto"

    def test_indent_parameter(self):
        ir = _make_minimal_ir()
        compact = to_json(ir, indent=0)
        pretty = to_json(ir, indent=4)
        # Pretty-printed version should be longer due to whitespace
        assert len(pretty) >= len(compact)


class TestFromJson:
    """from_json deserializes back to FaradayIR."""

    def test_round_trip(self):
        original = _make_minimal_ir()
        json_str = to_json(original)
        restored = from_json(json_str)
        assert isinstance(restored, FaradayIR)
        assert restored.metadata.protocol == original.metadata.protocol
        assert restored.metadata.version == original.metadata.version

    def test_round_trip_preserves_system(self):
        ir = _make_minimal_ir(
            system=IRSystem(
                electrodes=3,
                reference="Ag/AgCl",
                working=IRWorkingElectrode(material="Pt", area_m2=1e-4),
                electrolyte=IRElectrolyte(solute="H2SO4", concentration_mol_m3=500.0),
                counter="Pt wire",
            )
        )
        restored = from_json(to_json(ir))
        assert restored.system.reference == "Ag/AgCl"
        assert restored.system.working.material == "Pt"
        assert restored.system.working.area_m2 == pytest.approx(1e-4)
        assert isinstance(restored.system.electrolyte, IRElectrolyte)
        assert restored.system.electrolyte.concentration_mol_m3 == pytest.approx(500.0)

    def test_round_trip_preserves_steps(self):
        original = _make_minimal_ir()
        restored = from_json(to_json(original))
        step = restored.procedure[0].steps[0]
        assert step.technique == "cv"

    def test_round_trip_preserves_safety(self):
        ir = _make_minimal_ir(
            safety=IRSafety(
                max_current_A=0.1,
                voltage_window_V=(0.0, 1.8),
                temperature_limits_C=(10.0, 60.0),
            )
        )
        restored = from_json(to_json(ir))
        assert restored.safety is not None
        assert restored.safety.max_current_A == pytest.approx(0.1)

    def test_round_trip_preserves_variables(self):
        ir = _make_minimal_ir(
            variables=IRVariables(extractions={"eis1": "Ru", "eis1.Cdl": "fit.Cdl"})
        )
        restored = from_json(to_json(ir))
        assert restored.variables is not None
        assert restored.variables.extractions["eis1"] == "Ru"


class TestFileIO:
    """to_file and from_file round-trip through disk."""

    def test_to_file_creates_file(self, tmp_path: Path):
        ir = _make_minimal_ir()
        fpath = tmp_path / "test.ir.json"
        to_file(ir, fpath)
        assert fpath.exists()
        content = fpath.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_from_file_reads_back(self, tmp_path: Path):
        ir = _make_minimal_ir()
        fpath = tmp_path / "test.ir.json"
        to_file(ir, fpath)
        restored = from_file(fpath)
        assert isinstance(restored, FaradayIR)
        assert restored.metadata.protocol == ir.metadata.protocol

    def test_file_round_trip_preserves_all_fields(self, tmp_path: Path):
        ir = _make_minimal_ir(
            safety=IRSafety(max_current_A=0.5),
            variables=IRVariables(extractions={"x": "y"}),
        )
        fpath = tmp_path / "full.ir.json"
        to_file(ir, fpath)
        restored = from_file(fpath)
        assert restored.safety is not None
        assert restored.safety.max_current_A == pytest.approx(0.5)
        assert restored.variables is not None
        assert restored.variables.extractions == {"x": "y"}

    def test_file_is_valid_json(self, tmp_path: Path):
        ir = _make_minimal_ir()
        fpath = tmp_path / "valid.ir.json"
        to_file(ir, fpath)
        parsed = json.loads(fpath.read_text(encoding="utf-8"))
        assert "faraday_version" in parsed
