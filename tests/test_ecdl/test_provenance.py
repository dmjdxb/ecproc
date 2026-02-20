#!/usr/bin/env python3
"""
ECDL Provenance Test Suite

Tests provenance chain creation, hash linking, and verification.

Run with: pytest tests/test_ecdl/test_provenance.py -v
"""

from datetime import datetime

import pytest

from ecproc.ecdl.provenance import create_provenance_chain, verify_provenance
from ecproc.ir.hash import compute_ir_hash
from ecproc.ir.schema import (
    FaradayIR,
    IRMetadata,
    IRPhase,
    IRProvenance,
    IRStep,
    IRSystem,
    IRWorkingElectrode,
)

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_ir():
    """Sample FaradayIR for provenance testing."""
    return FaradayIR(
        faraday_version="1.0",
        metadata=IRMetadata(
            protocol="Provenance Test",
            version="1.0",
            created=datetime(2026, 1, 20, 14, 0, 0),
            ecproc_version="0.1.0",
            source_hash="sha256:aabbccdd",
        ),
        system=IRSystem(
            electrodes=3,
            reference="RHE",
            working=IRWorkingElectrode(material="RuO2"),
        ),
        procedure=[
            IRPhase(
                name="Test Phase",
                steps=[IRStep(technique="lsv")],
            ),
        ],
        provenance=IRProvenance(
            source_file="test_provenance.ecproc",
            source_hash="sha256:aabbccdd",
            parser_version="0.1.0",
        ),
    )


@pytest.fixture
def sample_ir_hash(sample_ir):
    """Pre-computed hash for the sample IR."""
    ir_data = sample_ir.model_dump()
    return compute_ir_hash(ir_data)


# =============================================================================
# HASH VERIFICATION TESTS
# =============================================================================

class TestVerifyProvenance:
    """Test IR hash verification."""

    def test_matching_hash_returns_true(self, sample_ir, sample_ir_hash):
        """verify_provenance returns True when hash matches."""
        assert verify_provenance(sample_ir, sample_ir_hash) is True

    def test_wrong_hash_returns_false(self, sample_ir):
        """verify_provenance returns False for incorrect hash."""
        wrong_hash = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
        assert verify_provenance(sample_ir, wrong_hash) is False

    def test_hash_is_deterministic(self, sample_ir):
        """Same IR always produces the same hash."""
        ir_data = sample_ir.model_dump()
        hash1 = compute_ir_hash(ir_data)
        hash2 = compute_ir_hash(ir_data)
        assert hash1 == hash2


# =============================================================================
# PROVENANCE CHAIN TESTS
# =============================================================================

class TestCreateProvenanceChain:
    """Test provenance chain creation."""

    def test_chain_contains_required_fields(self, sample_ir):
        """Chain includes source_file, source_hash, ir_hash, parser_version."""
        chain = create_provenance_chain("test_provenance.ecproc", sample_ir)
        assert "source_file" in chain
        assert "source_hash" in chain
        assert "ir_hash" in chain
        assert "parser_version" in chain

    def test_chain_source_file_matches(self, sample_ir):
        """Chain source_file matches the provided argument."""
        chain = create_provenance_chain("my_experiment.ecproc", sample_ir)
        assert chain["source_file"] == "my_experiment.ecproc"

    def test_chain_ir_hash_format(self, sample_ir):
        """IR hash in chain uses sha256: prefix."""
        chain = create_provenance_chain("test.ecproc", sample_ir)
        assert chain["ir_hash"].startswith("sha256:")
        # sha256 hex digest is 64 characters
        hex_part = chain["ir_hash"].split(":")[1]
        assert len(hex_part) == 64

    def test_chain_with_none_source_file(self, sample_ir):
        """Chain handles None source_file gracefully."""
        chain = create_provenance_chain(None, sample_ir)
        assert chain["source_file"] == ""

    def test_chain_hash_matches_direct_computation(self, sample_ir):
        """Chain ir_hash equals direct compute_ir_hash result."""
        chain = create_provenance_chain("test.ecproc", sample_ir)
        ir_data = sample_ir.model_dump()
        direct_hash = compute_ir_hash(ir_data)
        assert chain["ir_hash"] == direct_hash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
