"""Tests for validation engine level 3 and 4 paths."""

from __future__ import annotations

from datetime import datetime, timezone

from ecproc.ir.schema import (
    FaradayIR,
    IRMetadata,
    IRPhase,
    IRProvenance,
    IRSafety,
    IRStep,
    IRSystem,
)
from ecproc.validator.engine import ValidationEngine

_NOW = datetime.now(timezone.utc)


def _make_ir(*, safety: IRSafety | None = None) -> FaradayIR:
    return FaradayIR(
        faraday_version="1.0",
        metadata=IRMetadata(
            protocol="Test", version="1.0", created=_NOW,
            ecproc_version="0.1.0", source_hash="abc",
        ),
        system=IRSystem(electrodes=3, reference="RHE"),
        procedure=[
            IRPhase(
                name="P1",
                steps=[
                    IRStep(
                        technique="cv", vertex1=0.05, vertex2=1.2,
                        scan_rate=0.05, cycles=3,
                    )
                ],
            )
        ],
        safety=safety,
        provenance=IRProvenance(source_hash="abc", parser_version="0.1.0"),
    )


class TestEngineLevel3:
    """Test L3 safety validation path in engine."""

    def test_level3_runs_safety(self) -> None:
        engine = ValidationEngine()
        ir = _make_ir(safety=IRSafety(
            voltage_window_V=(-5.0, 5.0),
        ))
        result = engine.validate(ir, level=3)
        assert result.valid

    def test_level3_catches_safety_violation(self) -> None:
        engine = ValidationEngine()
        ir = _make_ir(safety=IRSafety(
            voltage_window_V=(0.1, 0.2),  # CV vertex1=0.05 is outside
        ))
        result = engine.validate(ir, level=3)
        assert not result.valid

    def test_level2_skips_safety(self) -> None:
        engine = ValidationEngine()
        ir = _make_ir(safety=IRSafety(
            voltage_window_V=(0.1, 0.2),  # Would fail L3
        ))
        result = engine.validate(ir, level=2)
        assert result.valid  # L3 not run


class TestEngineLevel4:
    """Test L4 hardware validation path in engine."""

    def test_level4_runs_hardware(self) -> None:
        engine = ValidationEngine()
        ir = _make_ir()
        hw = {
            "supported_techniques": ["cv", "eis", "lsv"],
            "potential_range_V": [-10.0, 10.0],
            "current_range_A": [-1.0, 1.0],
        }
        result = engine.validate(ir, level=4, hardware=hw)
        assert result.valid

    def test_level4_catches_unsupported_technique(self) -> None:
        engine = ValidationEngine()
        ir = _make_ir()
        hw = {
            "supported_techniques": ["eis"],  # No cv support
            "potential_range_V": [-10.0, 10.0],
        }
        result = engine.validate(ir, level=4, hardware=hw)
        assert not result.valid

    def test_level3_skips_hardware(self) -> None:
        engine = ValidationEngine()
        ir = _make_ir()
        hw = {"supported_techniques": ["eis"]}
        result = engine.validate(ir, level=3, hardware=hw)
        assert result.valid  # L4 not run

    def test_level4_without_hardware_profile(self) -> None:
        engine = ValidationEngine()
        ir = _make_ir()
        result = engine.validate(ir, level=4)
        assert result.valid  # No hw profile = skip L4

    def test_level1_only(self) -> None:
        engine = ValidationEngine()
        ir = _make_ir()
        result = engine.validate(ir, level=1)
        assert result.valid
