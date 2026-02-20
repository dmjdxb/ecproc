"""Tests for ecproc.validator.safety -- L3 safety validation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ecproc.ir.schema import (
    FaradayIR,
    IRLoop,
    IRMetadata,
    IRPhase,
    IRProvenance,
    IRReferenceMonitor,
    IRSafety,
    IRStep,
    IRSystem,
    IRThermalRunaway,
)
from ecproc.validator.errors import Severity, ValidationResult
from ecproc.validator.safety import validate_safety

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)


def _meta() -> IRMetadata:
    return IRMetadata(
        protocol="test", version="1.0", created=_NOW,
        ecproc_version="0.1.0", source_hash="sha256:abc",
    )


def _prov() -> IRProvenance:
    return IRProvenance(source_file=None, source_hash="sha256:abc", parser_version="0.1.0")


def _system() -> IRSystem:
    return IRSystem(electrodes=3, reference="RHE")


def _cv(**extras) -> IRStep:
    defaults = dict(scan_rate=0.05, vertex1=0.05, vertex2=1.2, cycles=3)
    defaults.update(extras)
    return IRStep(technique="cv", **defaults)


def _phase(name="test", steps=None) -> IRPhase:
    return IRPhase(name=name, steps=steps or [_cv()])


def _ir(
    steps=None,
    safety=None,
    phases=None,
) -> FaradayIR:
    if phases is None:
        phase_steps = steps or [_cv()]
        phases = [_phase(steps=phase_steps)]
    return FaradayIR(
        metadata=_meta(),
        system=_system(),
        procedure=phases,
        safety=safety,
        provenance=_prov(),
    )


def _has_error(result: ValidationResult, code: str) -> bool:
    return any(i.code == code and i.severity == Severity.ERROR for i in result.issues)


def _has_warning(result: ValidationResult, code: str) -> bool:
    return any(i.code == code and i.severity == Severity.WARNING for i in result.issues)


# ---------------------------------------------------------------------------
# No safety block
# ---------------------------------------------------------------------------


class TestNoSafetyBlock:
    """Behaviour when safety block is absent."""

    def test_no_safety_small_procedure_passes(self):
        """< 5 steps with no safety -> no warning."""
        ir = _ir(safety=None, steps=[_cv()])
        result = validate_safety(ir)
        assert result.valid
        assert not _has_warning(result, "SF001")

    def test_no_safety_large_procedure_warns(self):
        """> 5 steps with no safety -> SF001 warning."""
        steps = [_cv() for _ in range(6)]
        ir = _ir(safety=None, steps=steps)
        result = validate_safety(ir)
        assert result.valid  # Warning, not error
        assert _has_warning(result, "SF001")


# ---------------------------------------------------------------------------
# SF002: voltage_window bounds
# ---------------------------------------------------------------------------


class TestVoltageWindow:
    """SF002: voltage_window lower >= upper."""

    def test_inverted_window_fails(self):
        safety = IRSafety(voltage_window_V=(1.5, 0.5))
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert _has_error(result, "SF002")

    def test_equal_bounds_fails(self):
        safety = IRSafety(voltage_window_V=(1.0, 1.0))
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert _has_error(result, "SF002")

    def test_valid_window_passes(self):
        safety = IRSafety(voltage_window_V=(0.0, 1.8))
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert not _has_error(result, "SF002")

    def test_step_potential_outside_window_fails(self):
        """SF010: Step potential outside safety voltage window."""
        safety = IRSafety(voltage_window_V=(0.0, 1.0))
        step = _cv(vertex1=0.05, vertex2=1.5)  # vertex2 outside window
        ir = _ir(safety=safety, steps=[step])
        result = validate_safety(ir)
        assert _has_error(result, "SF010")

    def test_step_potential_inside_window_passes(self):
        safety = IRSafety(voltage_window_V=(0.0, 1.5))
        step = _cv(vertex1=0.05, vertex2=1.2)
        ir = _ir(safety=safety, steps=[step])
        result = validate_safety(ir)
        assert not _has_error(result, "SF010")


# ---------------------------------------------------------------------------
# SF003: max_current
# ---------------------------------------------------------------------------


class TestCurrentLimit:
    """SF003: max_current_A must be > 0; SF011: step currents within limit."""

    def test_zero_max_current_fails(self):
        safety = IRSafety(max_current_A=0.0)
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert _has_error(result, "SF003")

    def test_negative_max_current_fails(self):
        safety = IRSafety(max_current_A=-0.5)
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert _has_error(result, "SF003")

    def test_positive_max_current_passes(self):
        safety = IRSafety(max_current_A=0.1)
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert not _has_error(result, "SF003")

    def test_step_current_exceeds_limit_fails(self):
        """SF011: Step current exceeds safety max_current."""
        safety = IRSafety(max_current_A=0.1)
        step = IRStep(technique="galvanostatic", current=0.5)
        ir = _ir(safety=safety, steps=[step])
        result = validate_safety(ir)
        assert _has_error(result, "SF011")

    def test_step_current_within_limit_passes(self):
        safety = IRSafety(max_current_A=1.0)
        step = IRStep(technique="galvanostatic", current=0.5)
        ir = _ir(safety=safety, steps=[step])
        result = validate_safety(ir)
        assert not _has_error(result, "SF011")


# ---------------------------------------------------------------------------
# SF004/SF005/SF006: temperature limits
# ---------------------------------------------------------------------------


class TestTemperatureLimits:
    """Temperature limit validation."""

    def test_inverted_temperature_fails(self):
        safety = IRSafety(temperature_limits_C=(60.0, 10.0))
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert _has_error(result, "SF004")

    def test_equal_temperature_fails(self):
        safety = IRSafety(temperature_limits_C=(25.0, 25.0))
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert _has_error(result, "SF004")

    def test_valid_temperature_passes(self):
        safety = IRSafety(temperature_limits_C=(10.0, 60.0))
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert not _has_error(result, "SF004")

    def test_unusually_low_temperature_warns(self):
        """SF005: t_low < -40 C."""
        safety = IRSafety(temperature_limits_C=(-50.0, 25.0))
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert _has_warning(result, "SF005")

    def test_unusually_high_temperature_warns(self):
        """SF006: t_high > 200 C."""
        safety = IRSafety(temperature_limits_C=(20.0, 250.0))
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert _has_warning(result, "SF006")

    def test_normal_temperature_no_warning(self):
        safety = IRSafety(temperature_limits_C=(10.0, 80.0))
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert not _has_warning(result, "SF005")
        assert not _has_warning(result, "SF006")


# ---------------------------------------------------------------------------
# SF007: stop conditions for long procedures
# ---------------------------------------------------------------------------


class TestStopConditions:
    """SF007: Long procedure without stop_conditions."""

    def test_long_procedure_no_stop_warns(self):
        """More than 10 steps without stop_conditions."""
        steps = [_cv() for _ in range(11)]
        safety = IRSafety()  # No stop_conditions
        ir = _ir(safety=safety, steps=steps)
        result = validate_safety(ir)
        assert _has_warning(result, "SF007")

    def test_long_procedure_with_stop_no_warning(self):
        steps = [_cv() for _ in range(11)]
        safety = IRSafety(stop_conditions=["E_deviation > 50 mV"])
        ir = _ir(safety=safety, steps=steps)
        result = validate_safety(ir)
        assert not _has_warning(result, "SF007")


# ---------------------------------------------------------------------------
# SF008/SF009: thermal runaway
# ---------------------------------------------------------------------------


class TestThermalRunaway:
    """Thermal runaway settings validation."""

    def test_zero_rate_fails(self):
        """SF008: max_dT_dt_K_s must be > 0."""
        safety = IRSafety(
            thermal_runaway=IRThermalRunaway(max_dT_dt_K_s=0.0, action="cell_off")
        )
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert _has_error(result, "SF008")

    def test_negative_rate_fails(self):
        safety = IRSafety(
            thermal_runaway=IRThermalRunaway(max_dT_dt_K_s=-1.0, action="cell_off")
        )
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert _has_error(result, "SF008")

    def test_positive_rate_passes(self):
        safety = IRSafety(
            thermal_runaway=IRThermalRunaway(max_dT_dt_K_s=1.0, action="cell_off")
        )
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert not _has_error(result, "SF008")

    def test_nonstandard_action_warns(self):
        """SF009: Non-standard action string."""
        safety = IRSafety(
            thermal_runaway=IRThermalRunaway(max_dT_dt_K_s=1.0, action="beep")
        )
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert _has_warning(result, "SF009")

    @pytest.mark.parametrize("action", ["cell_off", "pause", "abort"])
    def test_standard_actions_no_warning(self, action):
        safety = IRSafety(
            thermal_runaway=IRThermalRunaway(max_dT_dt_K_s=1.0, action=action)
        )
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        assert not _has_warning(result, "SF009")


# ---------------------------------------------------------------------------
# Reference electrode monitor (no explicit validator code yet, but test IR construction)
# ---------------------------------------------------------------------------


class TestReferenceElectrodeMonitor:
    """Reference electrode monitor is accepted in safety block."""

    def test_reference_monitor_accepted(self):
        safety = IRSafety(
            reference_electrode_monitor=IRReferenceMonitor(
                max_Ru_change_factor=10.0,
                max_ocp_drift_V_s=0.5,
                action="cell_off",
            )
        )
        ir = _ir(safety=safety)
        result = validate_safety(ir)
        # Should not crash; monitor is accepted
        assert isinstance(result, ValidationResult)


# ---------------------------------------------------------------------------
# Valid safety block passes
# ---------------------------------------------------------------------------


class TestValidSafety:
    """A well-formed safety block produces no errors."""

    def test_full_safety_no_errors(self):
        safety = IRSafety(
            max_current_A=1.0,
            voltage_window_V=(-0.5, 2.0),
            temperature_limits_C=(15.0, 80.0),
            stop_conditions=["E_deviation > 50 mV"],
            thermal_runaway=IRThermalRunaway(max_dT_dt_K_s=1.0, action="cell_off"),
        )
        steps = [_cv(vertex1=0.05, vertex2=1.2)]
        ir = _ir(safety=safety, steps=steps)
        result = validate_safety(ir)
        assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# Potential window checks in loops
# ---------------------------------------------------------------------------


class TestPotentialWindowInLoops:
    """Voltage window checks inside loop structures."""

    def test_potential_in_loop_outside_window_fails(self):
        safety = IRSafety(voltage_window_V=(0.0, 1.0))
        step = _cv(vertex1=0.05, vertex2=1.5)
        loop = IRLoop(count=5, steps=[step])
        ir = _ir(safety=safety, phases=[_phase(steps=[loop])])
        result = validate_safety(ir)
        assert _has_error(result, "SF010")
