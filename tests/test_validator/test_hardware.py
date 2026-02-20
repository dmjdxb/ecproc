"""Tests for ecproc.validator.hardware -- L4 hardware profile validation."""

from __future__ import annotations

from datetime import datetime, timezone

from ecproc.ir.schema import (
    FaradayIR,
    IRLoop,
    IRMetadata,
    IRPhase,
    IRProvenance,
    IRStep,
    IRSystem,
)
from ecproc.validator.errors import Severity, ValidationResult
from ecproc.validator.hardware import validate_hardware

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


def _eis(**extras) -> IRStep:
    defaults = dict(f_start=1e5, f_end=0.1, amplitude=0.01)
    defaults.update(extras)
    return IRStep(technique="eis", **defaults)


def _phase(name="test", steps=None) -> IRPhase:
    return IRPhase(name=name, steps=steps or [_cv()])


def _ir(steps=None, loop=None) -> FaradayIR:
    if loop is not None:
        phase_steps = [loop]
    elif steps is not None:
        phase_steps = steps
    else:
        phase_steps = [_cv()]
    return FaradayIR(
        metadata=_meta(),
        system=_system(),
        procedure=[_phase(steps=phase_steps)],
        provenance=_prov(),
    )


def _has_error(result: ValidationResult, code: str) -> bool:
    return any(i.code == code and i.severity == Severity.ERROR for i in result.issues)


# Standard Gamry-like hardware profile
GAMRY_PROFILE = {
    "name": "Gamry Interface 1010E",
    "supported_techniques": ["cv", "eis", "lsv", "ocp", "hold", "galvanostatic"],
    "potential_range_V": [-12.0, 12.0],
    "current_range_A": [-1.0, 1.0],
    "frequency_range_Hz": [1e-5, 1e6],
    "max_channels": 1,
    "max_data_points": 65536,
}

# Restricted profile for testing failures
RESTRICTED_PROFILE = {
    "name": "Basic Potentiostat",
    "supported_techniques": ["cv", "ocp"],
    "potential_range_V": [-5.0, 5.0],
    "current_range_A": [-0.1, 0.1],
    "frequency_range_Hz": [0.01, 1e4],
}


# ---------------------------------------------------------------------------
# HW001: Technique support
# ---------------------------------------------------------------------------


class TestTechniqueSupport:
    """HW001: Technique not supported by hardware."""

    def test_supported_technique_passes(self):
        result = validate_hardware(_ir(steps=[_cv()]), GAMRY_PROFILE)
        assert not _has_error(result, "HW001")

    def test_unsupported_technique_fails(self):
        step = IRStep(technique="eis", f_start=1e5, f_end=0.1, amplitude=0.01)
        result = validate_hardware(_ir(steps=[step]), RESTRICTED_PROFILE)
        assert _has_error(result, "HW001")

    def test_multiple_unsupported_techniques(self):
        steps = [
            IRStep(technique="eis", f_start=1e5, f_end=0.1, amplitude=0.01),
            IRStep(technique="dpv"),
        ]
        result = validate_hardware(_ir(steps=steps), RESTRICTED_PROFILE)
        hw001_errors = [i for i in result.issues if i.code == "HW001"]
        assert len(hw001_errors) == 2

    def test_empty_supported_list_allows_all(self):
        """If supported_techniques is empty, no HW001 errors."""
        profile = {"supported_techniques": []}
        result = validate_hardware(_ir(steps=[_cv()]), profile)
        assert not _has_error(result, "HW001")


# ---------------------------------------------------------------------------
# HW002: Potential range
# ---------------------------------------------------------------------------


class TestPotentialRange:
    """HW002: Potential outside hardware range."""

    def test_potential_in_range_passes(self):
        result = validate_hardware(_ir(steps=[_cv()]), GAMRY_PROFILE)
        assert not _has_error(result, "HW002")

    def test_potential_outside_range_fails(self):
        step = _cv(vertex2=15.0)  # Exceeds GAMRY's +/-12 V
        result = validate_hardware(_ir(steps=[step]), GAMRY_PROFILE)
        assert _has_error(result, "HW002")

    def test_negative_potential_outside_range_fails(self):
        step = _cv(vertex1=-13.0)
        result = validate_hardware(_ir(steps=[step]), GAMRY_PROFILE)
        assert _has_error(result, "HW002")

    def test_restricted_potential_range(self):
        step = _cv(vertex1=-0.5, vertex2=6.0)  # 6.0 V exceeds restricted +/-5
        result = validate_hardware(_ir(steps=[step]), RESTRICTED_PROFILE)
        assert _has_error(result, "HW002")

    def test_no_potential_range_in_profile_skips(self):
        """If potential_range_V not in profile, skip HW002."""
        profile = {"supported_techniques": ["cv"]}
        step = _cv(vertex2=100.0)
        result = validate_hardware(_ir(steps=[step]), profile)
        assert not _has_error(result, "HW002")


# ---------------------------------------------------------------------------
# HW003: Current range
# ---------------------------------------------------------------------------


class TestCurrentRange:
    """HW003: Current outside hardware range."""

    def test_current_in_range_passes(self):
        step = IRStep(technique="galvanostatic", current=0.05)
        result = validate_hardware(_ir(steps=[step]), GAMRY_PROFILE)
        assert not _has_error(result, "HW003")

    def test_current_outside_range_fails(self):
        step = IRStep(technique="galvanostatic", current=2.0)  # Exceeds 1 A
        result = validate_hardware(_ir(steps=[step]), GAMRY_PROFILE)
        assert _has_error(result, "HW003")

    def test_negative_current_outside_range_fails(self):
        step = IRStep(technique="galvanostatic", current=-1.5)
        result = validate_hardware(_ir(steps=[step]), GAMRY_PROFILE)
        assert _has_error(result, "HW003")

    def test_restricted_current_range(self):
        step = IRStep(technique="galvanostatic", current=0.5)  # Exceeds restricted 0.1 A
        result = validate_hardware(_ir(steps=[step]), RESTRICTED_PROFILE)
        assert _has_error(result, "HW003")


# ---------------------------------------------------------------------------
# HW004: Frequency range (EIS)
# ---------------------------------------------------------------------------


class TestFrequencyRange:
    """HW004: Frequency outside hardware range."""

    def test_frequency_in_range_passes(self):
        result = validate_hardware(_ir(steps=[_eis()]), GAMRY_PROFILE)
        assert not _has_error(result, "HW004")

    def test_f_start_above_max_fails(self):
        step = _eis(f_start=2e6)  # Exceeds GAMRY 1e6 Hz max
        result = validate_hardware(_ir(steps=[step]), GAMRY_PROFILE)
        assert _has_error(result, "HW004")

    def test_f_end_below_min_fails(self):
        step = _eis(f_end=1e-6)  # Below GAMRY 1e-5 Hz min
        result = validate_hardware(_ir(steps=[step]), GAMRY_PROFILE)
        assert _has_error(result, "HW004")

    def test_non_eis_frequency_ignored(self):
        """Frequency check only applies to EIS technique."""
        step = IRStep(technique="cv", f_start=1e9)
        result = validate_hardware(_ir(steps=[step]), GAMRY_PROFILE)
        assert not _has_error(result, "HW004")


# ---------------------------------------------------------------------------
# Full hardware profile validation
# ---------------------------------------------------------------------------


class TestFullProfile:
    """End-to-end tests with complete hardware profile."""

    def test_valid_procedure_passes(self):
        steps = [_cv(), _eis()]
        result = validate_hardware(_ir(steps=steps), GAMRY_PROFILE)
        assert result.valid
        assert len(result.errors) == 0

    def test_loop_steps_validated(self):
        """Steps inside loops are also checked."""
        step = _cv(vertex2=15.0)
        loop = IRLoop(count=5, steps=[step])
        result = validate_hardware(_ir(loop=loop), GAMRY_PROFILE)
        assert _has_error(result, "HW002")

    def test_empty_profile_no_errors(self):
        """Empty profile dict should not crash."""
        result = validate_hardware(_ir(), {})
        assert isinstance(result, ValidationResult)
        assert len(result.errors) == 0

    def test_all_checks_combine(self):
        """Multiple violations produce multiple errors."""
        step = IRStep(technique="dpv", current=5.0, vertex1=20.0)
        result = validate_hardware(_ir(steps=[step]), GAMRY_PROFILE)
        codes = {i.code for i in result.errors}
        # dpv not supported -> HW001, vertex1=20 > 12 -> HW002, current=5 > 1 -> HW003
        assert "HW001" in codes
        assert "HW002" in codes
        assert "HW003" in codes
