"""Tests for ecproc.ecdl.serializer - ECDL JSON serialization/deserialization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ecproc.ecdl.schema import (
    ECDLDocument,
    ECDLElectrolyte,
    ECDLMaterial,
    ECDLObservation,
    ECDLProtocol,
    ECDLProvenance,
)
from ecproc.ecdl.serializer import from_file, from_json, to_file, to_json

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_doc() -> ECDLDocument:
    """Minimal valid ECDLDocument."""
    return ECDLDocument(
        material=ECDLMaterial(formula_raw="IrO2"),
        protocol=ECDLProtocol(name="Simple CV", version="1.0"),
    )


@pytest.fixture
def full_doc() -> ECDLDocument:
    """More complete ECDLDocument with observations and provenance."""
    return ECDLDocument(
        ecdl_version="1.0.0",
        id="test-001",
        material=ECDLMaterial(
            formula_raw="IrO2",
            formula_canonical="IrO2",
            composition={"Ir": 0.542, "O": 0.458},
            morphology="nanoparticle",
            support="carbon",
        ),
        protocol=ECDLProtocol(
            name="DOE OER AST",
            version="1.0",
            standard_reference="DOE/EERE",
            electrolyte=ECDLElectrolyte(
                type="H2SO4",
                concentration_M=0.5,
            ),
            ph=0.3,
            regime="acidic",
            temperature_C=80.0,
            duration_hours=100.0,
        ),
        observations=[
            ECDLObservation(
                tag="initial_cv",
                metric_type="peak_current",
                value=0.0012,
                unit="A",
            ),
            ECDLObservation(
                tag="final_cv",
                metric_type="peak_current",
                value=0.0008,
                unit="A",
            ),
        ],
        provenance=ECDLProvenance(
            doi="10.1234/example",
            title="Test Article",
            authors=["Smith, J.", "Doe, A."],
            journal="J. Test Chem.",
            year=2026,
        ),
    )


# ---------------------------------------------------------------------------
# to_json
# ---------------------------------------------------------------------------


class TestToJson:
    """Test serialization to JSON string."""

    def test_returns_string(self, minimal_doc: ECDLDocument):
        result = to_json(minimal_doc)
        assert isinstance(result, str)

    def test_produces_valid_json(self, minimal_doc: ECDLDocument):
        result = to_json(minimal_doc)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_contains_ecdl_version(self, minimal_doc: ECDLDocument):
        result = to_json(minimal_doc)
        parsed = json.loads(result)
        assert "ecdl_version" in parsed
        assert parsed["ecdl_version"] == "1.0.0"

    def test_contains_material(self, minimal_doc: ECDLDocument):
        result = to_json(minimal_doc)
        parsed = json.loads(result)
        assert "material" in parsed
        assert parsed["material"]["formula_raw"] == "IrO2"

    def test_contains_protocol(self, minimal_doc: ECDLDocument):
        result = to_json(minimal_doc)
        parsed = json.loads(result)
        assert "protocol" in parsed
        assert parsed["protocol"]["name"] == "Simple CV"

    def test_full_doc_serializes(self, full_doc: ECDLDocument):
        result = to_json(full_doc)
        parsed = json.loads(result)
        assert parsed["id"] == "test-001"
        assert len(parsed["observations"]) == 2

    def test_custom_indent(self, minimal_doc: ECDLDocument):
        result_2 = to_json(minimal_doc, indent=2)
        result_4 = to_json(minimal_doc, indent=4)
        # Both are valid JSON
        json.loads(result_2)
        json.loads(result_4)
        # Different indent leads to different string length
        # (4-indent should be longer due to more whitespace)
        assert len(result_4) >= len(result_2)


# ---------------------------------------------------------------------------
# from_json
# ---------------------------------------------------------------------------


class TestFromJson:
    """Test deserialization from JSON string."""

    def test_returns_ecdl_document(self, minimal_doc: ECDLDocument):
        json_str = to_json(minimal_doc)
        result = from_json(json_str)
        assert isinstance(result, ECDLDocument)

    def test_preserves_material(self, minimal_doc: ECDLDocument):
        json_str = to_json(minimal_doc)
        result = from_json(json_str)
        assert result.material.formula_raw == "IrO2"

    def test_preserves_protocol(self, minimal_doc: ECDLDocument):
        json_str = to_json(minimal_doc)
        result = from_json(json_str)
        assert result.protocol.name == "Simple CV"
        assert result.protocol.version == "1.0"

    def test_preserves_ecdl_version(self, minimal_doc: ECDLDocument):
        json_str = to_json(minimal_doc)
        result = from_json(json_str)
        assert result.ecdl_version == "1.0.0"


# ---------------------------------------------------------------------------
# Round-trip (to_json -> from_json)
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Test JSON round-trip serialization."""

    def test_minimal_round_trip(self, minimal_doc: ECDLDocument):
        json_str = to_json(minimal_doc)
        restored = from_json(json_str)
        assert restored.material.formula_raw == minimal_doc.material.formula_raw
        assert restored.protocol.name == minimal_doc.protocol.name

    def test_full_doc_round_trip(self, full_doc: ECDLDocument):
        json_str = to_json(full_doc)
        restored = from_json(json_str)
        assert restored.id == full_doc.id
        assert restored.material.formula_raw == full_doc.material.formula_raw
        assert restored.material.morphology == full_doc.material.morphology
        assert restored.protocol.electrolyte.type == "H2SO4"
        assert restored.protocol.electrolyte.concentration_M == pytest.approx(0.5)
        assert len(restored.observations) == 2
        assert restored.provenance.doi == "10.1234/example"
        assert restored.provenance.year == 2026

    def test_double_round_trip(self, full_doc: ECDLDocument):
        """Serialize, deserialize, serialize again -- output should be identical."""
        json1 = to_json(full_doc)
        restored = from_json(json1)
        json2 = to_json(restored)
        assert json1 == json2

    def test_observation_values_preserved(self, full_doc: ECDLDocument):
        json_str = to_json(full_doc)
        restored = from_json(json_str)
        for orig, rest in zip(full_doc.observations, restored.observations):
            assert orig.tag == rest.tag
            assert orig.metric_type == rest.metric_type
            assert orig.value == pytest.approx(rest.value)
            assert orig.unit == rest.unit


# ---------------------------------------------------------------------------
# to_file / from_file
# ---------------------------------------------------------------------------


class TestFileIO:
    """Test file-based serialization."""

    def test_to_file_creates_file(self, minimal_doc: ECDLDocument, tmp_path: Path):
        filepath = tmp_path / "test.ecdl.json"
        to_file(minimal_doc, filepath)
        assert filepath.exists()

    def test_to_file_writes_valid_json(self, minimal_doc: ECDLDocument, tmp_path: Path):
        filepath = tmp_path / "test.ecdl.json"
        to_file(minimal_doc, filepath)
        content = filepath.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_from_file_returns_document(self, minimal_doc: ECDLDocument, tmp_path: Path):
        filepath = tmp_path / "test.ecdl.json"
        to_file(minimal_doc, filepath)
        result = from_file(filepath)
        assert isinstance(result, ECDLDocument)

    def test_file_round_trip(self, full_doc: ECDLDocument, tmp_path: Path):
        filepath = tmp_path / "full.ecdl.json"
        to_file(full_doc, filepath)
        restored = from_file(filepath)
        assert restored.id == full_doc.id
        assert restored.material.formula_raw == full_doc.material.formula_raw
        assert len(restored.observations) == len(full_doc.observations)

    def test_to_file_accepts_string_path(self, minimal_doc: ECDLDocument, tmp_path: Path):
        filepath = str(tmp_path / "string_path.ecdl.json")
        to_file(minimal_doc, filepath)
        assert Path(filepath).exists()

    def test_from_file_accepts_string_path(self, minimal_doc: ECDLDocument, tmp_path: Path):
        filepath = tmp_path / "string_read.ecdl.json"
        to_file(minimal_doc, filepath)
        result = from_file(str(filepath))
        assert isinstance(result, ECDLDocument)

    def test_to_file_with_custom_indent(self, minimal_doc: ECDLDocument, tmp_path: Path):
        path_2 = tmp_path / "indent2.json"
        path_4 = tmp_path / "indent4.json"
        to_file(minimal_doc, path_2, indent=2)
        to_file(minimal_doc, path_4, indent=4)
        # Both should be valid
        from_file(path_2)
        from_file(path_4)

    def test_from_file_nonexistent_raises(self):
        with pytest.raises(Exception):
            from_file("/nonexistent/path/test.ecdl.json")
