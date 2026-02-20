"""Shared test fixtures for ecproc."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from ecproc.ir.schema import (
    FaradayIR,
    IRMetadata,
    IRPhase,
    IRProvenance,
    IRStep,
    IRSystem,
)
from ecproc.parser.ast import (
    MetadataAST,
    PhaseAST,
    ProcedureAST,
    StepAST,
    SystemAST,
)

FIXTURES_DIR = Path(__file__).parent / "test_parser" / "fixtures"


@pytest.fixture
def simple_procedure_ast() -> ProcedureAST:
    """A minimal valid ProcedureAST for testing."""
    return ProcedureAST(
        metadata=MetadataAST(protocol="Test Protocol", version="1.0"),
        system=SystemAST(electrodes=3, reference="RHE"),
        procedure=[
            PhaseAST(
                name="Conditioning",
                steps=[
                    StepAST(
                        technique="cv",
                        parameters={
                            "vertex1": "0.05 V",
                            "vertex2": "1.2 V",
                            "rate": "50 mV/s",
                            "cycles": 20,
                        },
                    )
                ],
            )
        ],
    )


@pytest.fixture
def simple_faraday_ir() -> FaradayIR:
    """A minimal valid FaradayIR for testing."""
    return FaradayIR(
        faraday_version="1.0",
        metadata=IRMetadata(
            protocol="Test Protocol",
            version="1.0",
            created=datetime(2024, 1, 1, tzinfo=timezone.utc),
            ecproc_version="0.1.0",
            source_hash="abc123",
        ),
        system=IRSystem(electrodes=3, reference="RHE"),
        procedure=[
            IRPhase(
                name="Conditioning",
                steps=[
                    IRStep(
                        technique="cv",
                        vertex1=0.05,
                        vertex2=1.2,
                        scan_rate_V_s=0.05,
                        cycles=20,
                    )
                ],
            )
        ],
        provenance=IRProvenance(
            source_hash="abc123",
            parser_version="0.1.0",
        ),
    )
