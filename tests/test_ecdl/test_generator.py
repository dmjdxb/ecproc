#!/usr/bin/env python3
"""
ECDL Generator Test Suite

Tests generation of ECDL records from FaradayIR + ExecutionResult.

Run with: pytest tests/test_ecdl/test_generator.py -v
"""

from datetime import datetime

import pytest

from ecproc.ecdl.generator import generate_ecdl
from ecproc.ecdl.schema import (
    ECDLDocument,
)
from ecproc.ir.schema import (
    FaradayIR,
    IRElectrolyte,
    IRMetadata,
    IRPhase,
    IRProvenance,
    IRStep,
    IRSystem,
    IRWorkingElectrode,
)
from ecproc.targets.base import ExecutionResult

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def simple_ir():
    """Minimal valid FaradayIR document."""
    return FaradayIR(
        faraday_version="1.0",
        metadata=IRMetadata(
            protocol="Simple CV",
            version="1.0",
            created=datetime(2026, 1, 15, 10, 0, 0),
            ecproc_version="0.1.0",
            source_hash="sha256:abc123",
        ),
        system=IRSystem(
            electrodes=3,
            reference="RHE",
            working=IRWorkingElectrode(material="IrO2"),
            electrolyte=IRElectrolyte(solute="H2SO4", concentration_mol_m3=500.0),
        ),
        procedure=[
            IRPhase(
                name="Conditioning",
                steps=[
                    IRStep(technique="cv", tag="conditioning_cv"),
                ],
            ),
        ],
        provenance=IRProvenance(
            source_file="simple_cv.ecproc",
            source_hash="sha256:abc123",
            parser_version="0.1.0",
        ),
    )


@pytest.fixture
def simple_results():
    """Minimal valid ExecutionResult."""
    return ExecutionResult(
        success=True,
        target="biologic",
        observations=[
            {
                "tag": "conditioning_cv",
                "data": {
                    "peak_current_A": 0.0012,
                    "charge_C": 0.05,
                },
            },
        ],
        data_files=["data/cv_001.mpt"],
        started="2026-01-15T10:00:00Z",
        completed="2026-01-15T10:30:00Z",
        hardware="BioLogic SP-300",
    )


@pytest.fixture
def ir_no_working():
    """IR with no working electrode."""
    return FaradayIR(
        faraday_version="1.0",
        metadata=IRMetadata(
            protocol="Bare Electrode",
            version="1.0",
            created=datetime(2026, 1, 15),
            ecproc_version="0.1.0",
            source_hash="sha256:def456",
        ),
        system=IRSystem(
            electrodes=3,
            reference="RHE",
        ),
        procedure=[
            IRPhase(name="Test", steps=[IRStep(technique="ocp")]),
        ],
        provenance=IRProvenance(
            source_file="bare.ecproc",
            source_hash="sha256:def456",
            parser_version="0.1.0",
        ),
    )


@pytest.fixture
def ir_string_electrolyte():
    """IR with string-type electrolyte (not IRElectrolyte object)."""
    return FaradayIR(
        faraday_version="1.0",
        metadata=IRMetadata(
            protocol="String Electrolyte Test",
            version="1.0",
            created=datetime(2026, 2, 1),
            ecproc_version="0.1.0",
            source_hash="sha256:ghi789",
        ),
        system=IRSystem(
            electrodes=3,
            reference="RHE",
            working=IRWorkingElectrode(material="Pt/C"),
            electrolyte="0.1 M HClO4",
        ),
        procedure=[
            IRPhase(name="Test", steps=[IRStep(technique="cv")]),
        ],
        provenance=IRProvenance(
            source_file="string_elyte.ecproc",
            source_hash="sha256:ghi789",
            parser_version="0.1.0",
        ),
    )


@pytest.fixture
def empty_results():
    """ExecutionResult with no observations."""
    return ExecutionResult(
        success=True,
        target="gamry",
        observations=[],
        started="2026-01-15T11:00:00Z",
        completed="2026-01-15T11:05:00Z",
        hardware="Gamry Interface 1010E",
    )


# =============================================================================
# BASIC GENERATION TESTS
# =============================================================================

class TestGenerateECDL:
    """Test core ECDL generation from IR + results."""

    def test_returns_ecdl_document(self, simple_ir, simple_results):
        """generate_ecdl returns an ECDLDocument instance."""
        doc = generate_ecdl(simple_ir, simple_results)
        assert isinstance(doc, ECDLDocument)

    def test_ecdl_version_set(self, simple_ir, simple_results):
        """Generated document has ECDL version."""
        doc = generate_ecdl(simple_ir, simple_results)
        assert doc.ecdl_version == "1.0.0"

    def test_material_from_working_electrode(self, simple_ir, simple_results):
        """Material formula comes from IR working electrode."""
        doc = generate_ecdl(simple_ir, simple_results)
        assert doc.material.formula_raw == "IrO2"

    def test_material_unknown_when_no_working(self, ir_no_working, empty_results):
        """Material is 'unknown' when IR has no working electrode."""
        doc = generate_ecdl(ir_no_working, empty_results)
        assert doc.material.formula_raw == "unknown"

    def test_protocol_name_and_version(self, simple_ir, simple_results):
        """Protocol name and version from IR metadata."""
        doc = generate_ecdl(simple_ir, simple_results)
        assert doc.protocol.name == "Simple CV"
        assert doc.protocol.version == "1.0"


# =============================================================================
# ELECTROLYTE HANDLING TESTS
# =============================================================================

class TestElectrolyteHandling:
    """Test electrolyte information propagation."""

    def test_electrolyte_from_ir_object(self, simple_ir, simple_results):
        """Electrolyte data propagated from IRElectrolyte object."""
        doc = generate_ecdl(simple_ir, simple_results)
        assert doc.protocol.electrolyte is not None
        assert doc.protocol.electrolyte.type == "H2SO4"
        assert doc.protocol.electrolyte.concentration_M == pytest.approx(0.5)

    def test_no_electrolyte_for_string_type(self, ir_string_electrolyte, empty_results):
        """String electrolyte in IR does not produce ECDL electrolyte."""
        doc = generate_ecdl(ir_string_electrolyte, empty_results)
        # String electrolyte is not an IRElectrolyte, so conversion is skipped
        assert doc.protocol.electrolyte is None


# =============================================================================
# OBSERVATION TESTS
# =============================================================================

class TestObservations:
    """Test observation extraction from execution results."""

    def test_observations_extracted(self, simple_ir, simple_results):
        """Observations are extracted from results data dicts."""
        doc = generate_ecdl(simple_ir, simple_results)
        assert doc.observations is not None
        assert len(doc.observations) == 2  # peak_current_A and charge_C

    def test_observation_tags_preserved(self, simple_ir, simple_results):
        """Observation tags match the source data."""
        doc = generate_ecdl(simple_ir, simple_results)
        tags = [obs.tag for obs in doc.observations]
        assert all(t == "conditioning_cv" for t in tags)

    def test_observation_values_are_float(self, simple_ir, simple_results):
        """Observation values are converted to float."""
        doc = generate_ecdl(simple_ir, simple_results)
        for obs in doc.observations:
            assert isinstance(obs.value, float)

    def test_no_observations_from_empty_results(self, simple_ir, empty_results):
        """Empty results produce empty observations list."""
        doc = generate_ecdl(simple_ir, empty_results)
        assert doc.observations is not None
        assert len(doc.observations) == 0


# =============================================================================
# PROVENANCE TESTS
# =============================================================================

class TestProvenance:
    """Test provenance chain in generated ECDL."""

    def test_provenance_present(self, simple_ir, simple_results):
        """Generated document includes provenance."""
        doc = generate_ecdl(simple_ir, simple_results)
        assert doc.provenance is not None

    def test_faraday_provenance(self, simple_ir, simple_results):
        """Faraday provenance links back to IR."""
        doc = generate_ecdl(simple_ir, simple_results)
        fp = doc.provenance.faraday
        assert fp is not None
        assert fp.procedure_name == "Simple CV"
        assert fp.procedure_version == "1.0"
        assert fp.ir_hash.startswith("sha256:")
        assert fp.source_file == "simple_cv.ecproc"

    def test_execution_provenance(self, simple_ir, simple_results):
        """Execution provenance captures timing and hardware."""
        doc = generate_ecdl(simple_ir, simple_results)
        ep = doc.provenance.execution
        assert ep is not None
        assert ep.started == "2026-01-15T10:00:00Z"
        assert ep.completed == "2026-01-15T10:30:00Z"
        assert ep.hardware == "BioLogic SP-300"

    def test_ir_hash_is_deterministic(self, simple_ir, simple_results):
        """Same IR produces same hash across calls."""
        doc1 = generate_ecdl(simple_ir, simple_results)
        doc2 = generate_ecdl(simple_ir, simple_results)
        assert doc1.provenance.faraday.ir_hash == doc2.provenance.faraday.ir_hash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
