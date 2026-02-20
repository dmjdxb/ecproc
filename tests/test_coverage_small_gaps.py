"""Tests covering small uncovered lines across many files for 100% coverage."""

from datetime import datetime, timezone

import pytest

from ecproc.ir.schema import (
    FaradayIR,
    IRLoop,
    IRMetadata,
    IRPhase,
    IRProvenance,
    IRSafety,
    IRStep,
    IRSystem,
)

# ---------------------------------------------------------------------------
# Shared helpers for building minimal FaradayIR instances
# ---------------------------------------------------------------------------

def _meta(**overrides):
    defaults = dict(
        protocol="Test",
        version="1.0",
        created=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ecproc_version="0.1.0",
        source_hash="abc",
    )
    defaults.update(overrides)
    return IRMetadata(**defaults)


def _prov():
    return IRProvenance(source_hash="abc", parser_version="0.1.0")


def _system():
    return IRSystem(electrodes=3, reference="RHE")


# ===================================================================
# 1. safety.py lines 250-255, 265-274 -- loop current limit check
# ===================================================================
class TestSafetyCurrentLimitInLoop:
    """validate_safety must walk into IRLoop steps and flag current violations."""

    def test_loop_step_exceeds_max_current(self):
        from ecproc.validator.safety import validate_safety

        ir = FaradayIR(
            faraday_version="1.0",
            metadata=_meta(),
            system=_system(),
            procedure=[
                IRPhase(
                    name="P1",
                    steps=[
                        IRLoop(
                            count=10,
                            steps=[
                                IRStep(technique="galvanostatic", current=1.0),
                            ],
                        )
                    ],
                )
            ],
            safety=IRSafety(max_current_A=0.5),
            provenance=_prov(),
        )
        result = validate_safety(ir)
        # Should have errors about current exceeding the limit
        assert not result.valid
        assert len(result.errors) > 0
        combined = " ".join(e.message for e in result.errors).lower()
        assert "current" in combined

    def test_loop_step_within_limit_no_error(self):
        from ecproc.validator.safety import validate_safety

        ir = FaradayIR(
            faraday_version="1.0",
            metadata=_meta(),
            system=_system(),
            procedure=[
                IRPhase(
                    name="P1",
                    steps=[
                        IRLoop(
                            count=3,
                            steps=[
                                IRStep(technique="galvanostatic", current=0.1),
                            ],
                        )
                    ],
                )
            ],
            safety=IRSafety(max_current_A=0.5),
            provenance=_prov(),
        )
        result = validate_safety(ir)
        current_errors = [
            e for e in result.errors if "current" in e.message.lower()
        ]
        assert len(current_errors) == 0


# ===================================================================
# 2. engine.py line 37 -- L1 errors cause early return
# ===================================================================
class TestValidationEngineL1EarlyReturn:
    def test_empty_procedure_triggers_l1_error(self):
        from ecproc.validator.engine import ValidationEngine

        ir = FaradayIR(
            faraday_version="1.0",
            metadata=_meta(),
            system=_system(),
            procedure=[],  # empty -> L1 failure (SYN005)
            provenance=_prov(),
        )
        engine = ValidationEngine()
        result = engine.validate(ir)
        # Should have errors and return early (no L2/L3 checks)
        assert not result.valid
        assert len(result.errors) > 0
        # Check that it's an L1 error
        assert any(e.level == "L1" for e in result.errors)


# ===================================================================
# 3. errors.py line 65 -- add_info()
# ===================================================================
class TestValidationResultAddInfo:
    def test_add_info(self):
        from ecproc.validator.errors import Severity, ValidationResult

        result = ValidationResult()
        result.add_info("L1", "INF001", "Just informational", path="metadata.protocol")
        # The info should be in the issues list
        info_issues = [i for i in result.issues if i.severity == Severity.INFO]
        assert len(info_issues) == 1
        assert info_issues[0].message == "Just informational"
        assert info_issues[0].code == "INF001"
        # add_info should not set valid to False
        assert result.valid is True


# ===================================================================
# 4. parser/errors.py lines 61-63 -- InvalidSyntaxError
# ===================================================================
class TestInvalidSyntaxError:
    def test_instantiate_no_location(self):
        from ecproc.parser.errors import InvalidSyntaxError

        err = InvalidSyntaxError(detail="unexpected token")
        assert err.detail == "unexpected token"
        assert "unexpected token" in str(err)

    def test_instantiate_with_location(self):
        from ecproc.parser.ast import SourceLocation
        from ecproc.parser.errors import InvalidSyntaxError

        loc = SourceLocation(line=10, column=5, file="test.ecproc")
        err = InvalidSyntaxError(detail="bad syntax", location=loc)
        assert err.location is not None
        assert err.location.line == 10
        assert "bad syntax" in str(err)


# ===================================================================
# 5. utils/time.py line 47 -- unknown duration unit raises ValueError
# ===================================================================
class TestParseDurationUnknownUnit:
    def test_unknown_unit_raises(self):
        from ecproc.utils.time import parse_duration

        with pytest.raises(ValueError):
            parse_duration("10 xyz")

    def test_known_units_work(self):
        from ecproc.utils.time import parse_duration

        # Sanity check that valid units don't raise
        result = parse_duration("10 s")
        assert result > 0


# ===================================================================
# 6. targets/base.py line 63 -- validate_ir() default returns []
# ===================================================================
class TestECProcTargetBaseValidateIR:
    def test_default_validate_ir_returns_empty(self):
        from ecproc.targets.base import CompilationResult, ECProcTarget, ExecutionResult

        class DummyTarget(ECProcTarget):
            """Minimal subclass that doesn't override validate_ir."""

            @property
            def name(self) -> str:
                return "dummy"

            @property
            def version(self) -> str:
                return "0.0.1"

            def capabilities(self):
                return {}

            def compile(self, ir):
                return CompilationResult(target="dummy", output={})

            def execute(self, compiled):
                return ExecutionResult(success=True, target="dummy")

        target = DummyTarget()
        ir = FaradayIR(
            faraday_version="1.0",
            metadata=_meta(),
            system=_system(),
            procedure=[
                IRPhase(
                    name="P1",
                    steps=[IRStep(technique="cv", vertex1=0.0, vertex2=1.0, scan_rate_V_s=0.05)],
                )
            ],
            provenance=_prov(),
        )
        result = target.validate_ir(ir)
        assert result == []


# ===================================================================
# 7. sdk/phase.py line 158 -- checkpoint() no-op
# ===================================================================
class TestPhaseCheckpoint:
    def test_checkpoint_is_noop(self):
        from ecproc.sdk.phase import Phase

        phase = Phase(name="test_phase")
        # Should not raise; it's a no-op
        result = phase.checkpoint("my_label")
        assert result is None


# ===================================================================
# 8. Technique validate_params -- various missing/invalid params
# ===================================================================

# CA is actually named "Hold" in ca.py
class TestHoldValidateParams:
    def test_missing_duration_error(self):
        from ecproc.sdk.techniques.ca import Hold

        hold = Hold(potential=0.5, duration="")
        errors = hold.validate_params()
        assert any("uration" in e for e in errors)

    def test_valid_hold_no_duration_error(self):
        from ecproc.sdk.techniques.ca import Hold

        hold = Hold(potential=0.5, duration="60 s")
        errors = hold.validate_params()
        duration_errors = [e for e in errors if "uration" in e]
        assert len(duration_errors) == 0


# CP is actually named "Galvanostatic" in cp.py
class TestGalvanostaticValidateParams:
    def test_missing_duration_error(self):
        from ecproc.sdk.techniques.cp import Galvanostatic

        galv = Galvanostatic(current=0.001, duration="")
        errors = galv.validate_params()
        assert any("uration" in e for e in errors)


class TestDPVValidateParams:
    def test_pulse_height_zero_error(self):
        from ecproc.sdk.techniques.dpv import DPV

        dpv = DPV(start=0.0, end=0.5, step=5.0, pulse_height=0, pulse_width=50.0)
        errors = dpv.validate_params()
        assert any("ulse height" in e for e in errors)

    def test_pulse_width_zero_error(self):
        from ecproc.sdk.techniques.dpv import DPV

        dpv = DPV(start=0.0, end=0.5, step=5.0, pulse_height=50.0, pulse_width=0)
        errors = dpv.validate_params()
        assert any("ulse width" in e for e in errors)

    def test_both_zero(self):
        from ecproc.sdk.techniques.dpv import DPV

        dpv = DPV(start=0.0, end=0.5, step=5.0, pulse_height=0, pulse_width=0)
        errors = dpv.validate_params()
        assert len(errors) >= 2


class TestEISValidateParams:
    def test_amplitude_zero_error(self):
        from ecproc.sdk.techniques.eis import EIS

        eis = EIS(f_start=100000, f_end=0.1, amplitude=0, ppd=10)
        errors = eis.validate_params()
        assert any("mplitude" in e for e in errors)


class TestGCDValidateParams:
    def test_negative_rest_between_error(self):
        from ecproc.sdk.techniques.gcd import GCD

        gcd = GCD(current=0.001, cycles=10, rest_between=-1)
        errors = gcd.validate_params()
        assert any("est" in e for e in errors)


class TestSWVValidateParams:
    def test_frequency_zero_error(self):
        from ecproc.sdk.techniques.swv import SWV

        swv = SWV(start=0.0, end=0.5, frequency=0, amplitude=25.0, step=4.0)
        errors = swv.validate_params()
        assert any("requency" in e for e in errors)

    def test_step_zero_error(self):
        from ecproc.sdk.techniques.swv import SWV

        swv = SWV(start=0.0, end=0.5, frequency=25, amplitude=25.0, step=0)
        errors = swv.validate_params()
        assert any("tep" in e for e in errors)

    def test_both_zero(self):
        from ecproc.sdk.techniques.swv import SWV

        swv = SWV(start=0.0, end=0.5, frequency=0, amplitude=25.0, step=0)
        errors = swv.validate_params()
        assert len(errors) >= 2
