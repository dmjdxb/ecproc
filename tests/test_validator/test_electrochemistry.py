"""Tests for ecproc.validator.electrochemistry -- L2 parameter/domain rules."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ecproc.ir.schema import (
    FaradayIR,
    IRLoop,
    IRMetadata,
    IRPhase,
    IRProvenance,
    IRStep,
    IRSystem,
)
from ecproc.validator.electrochemistry import (
    get_registry,
    validate_electrochemistry,
)
from ecproc.validator.errors import Severity, ValidationResult

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


def _ir(steps=None, loop=None) -> FaradayIR:
    """Build IR with a single phase containing the given steps or loop."""
    if loop is not None:
        phase_steps = [loop]
    elif steps is not None:
        phase_steps = steps
    else:
        phase_steps = [IRStep(technique="cv", scan_rate=0.05, vertex1=0.05, vertex2=1.2, cycles=3)]
    return FaradayIR(
        metadata=_meta(),
        system=_system(),
        procedure=[IRPhase(name="test", steps=phase_steps)],
        provenance=_prov(),
    )


def _cv(**extras) -> IRStep:
    """Create a CV step with given extras."""
    defaults = dict(scan_rate=0.05, vertex1=0.05, vertex2=1.2, cycles=3)
    defaults.update(extras)
    return IRStep(technique="cv", **defaults)


def _eis(**extras) -> IRStep:
    """Create an EIS step with given extras."""
    defaults = dict(f_start=1e5, f_end=0.1, amplitude=0.01)
    defaults.update(extras)
    return IRStep(technique="eis", **defaults)


def _hold(**extras) -> IRStep:
    defaults = dict(potential=0.5, duration=60.0)
    defaults.update(extras)
    return IRStep(technique="hold", **defaults)


def _ocp(**extras) -> IRStep:
    defaults = dict(duration=60.0)
    defaults.update(extras)
    return IRStep(technique="ocp", **defaults)


def _has_error(result: ValidationResult, code: str) -> bool:
    return any(i.code == code and i.severity == Severity.ERROR for i in result.issues)


def _has_warning(result: ValidationResult, code: str) -> bool:
    return any(i.code == code and i.severity == Severity.WARNING for i in result.issues)


# ---------------------------------------------------------------------------
# PV001: CV scan_rate > 10 V/s
# ---------------------------------------------------------------------------


class TestPV001:
    """PV001: CV scan_rate > 10 V/s -> error."""

    def test_scan_rate_above_max_fails(self):
        result = validate_electrochemistry(_ir(steps=[_cv(scan_rate=11.0)]))
        assert _has_error(result, "PV001")

    def test_scan_rate_at_max_passes(self):
        result = validate_electrochemistry(_ir(steps=[_cv(scan_rate=10.0)]))
        assert not _has_error(result, "PV001")

    def test_scan_rate_below_max_passes(self):
        result = validate_electrochemistry(_ir(steps=[_cv(scan_rate=0.05)]))
        assert not _has_error(result, "PV001")

    def test_non_cv_ignored(self):
        """EIS scan_rate should not trigger PV001."""
        step = IRStep(technique="eis", scan_rate=20.0, f_start=1e5, f_end=0.1, amplitude=0.01)
        result = validate_electrochemistry(_ir(steps=[step]))
        assert not _has_error(result, "PV001")


# ---------------------------------------------------------------------------
# PV002: CV scan_rate < 0.0001 V/s
# ---------------------------------------------------------------------------


class TestPV002:
    """PV002: CV scan_rate below minimum."""

    def test_scan_rate_below_min_fails(self):
        result = validate_electrochemistry(_ir(steps=[_cv(scan_rate=0.00001)]))
        assert _has_error(result, "PV002")

    def test_scan_rate_at_min_passes(self):
        result = validate_electrochemistry(_ir(steps=[_cv(scan_rate=0.0001)]))
        assert not _has_error(result, "PV002")


# ---------------------------------------------------------------------------
# PV003: CV cycles <= 0
# ---------------------------------------------------------------------------


class TestPV003:
    """PV003: CV cycles must be > 0."""

    @pytest.mark.parametrize("c", [0, -1, -10])
    def test_non_positive_cycles_fail(self, c):
        result = validate_electrochemistry(_ir(steps=[_cv(cycles=c)]))
        assert _has_error(result, "PV003")

    def test_positive_cycles_pass(self):
        result = validate_electrochemistry(_ir(steps=[_cv(cycles=1)]))
        assert not _has_error(result, "PV003")


# ---------------------------------------------------------------------------
# PV004: CV vertex1 == vertex2
# ---------------------------------------------------------------------------


class TestPV004:
    """PV004: vertex1 must differ from vertex2."""

    def test_equal_vertices_fail(self):
        result = validate_electrochemistry(_ir(steps=[_cv(vertex1=0.5, vertex2=0.5)]))
        assert _has_error(result, "PV004")

    def test_different_vertices_pass(self):
        result = validate_electrochemistry(_ir(steps=[_cv(vertex1=0.05, vertex2=1.2)]))
        assert not _has_error(result, "PV004")


# ---------------------------------------------------------------------------
# PV005: EIS f_start <= f_end
# ---------------------------------------------------------------------------


class TestPV005:
    """PV005: EIS f_start must be > f_end (high-to-low sweep)."""

    def test_f_start_less_than_f_end_fails(self):
        result = validate_electrochemistry(_ir(steps=[_eis(f_start=0.01, f_end=1e5)]))
        assert _has_error(result, "PV005")

    def test_f_start_equal_f_end_fails(self):
        result = validate_electrochemistry(_ir(steps=[_eis(f_start=100.0, f_end=100.0)]))
        assert _has_error(result, "PV005")

    def test_f_start_greater_than_f_end_passes(self):
        result = validate_electrochemistry(_ir(steps=[_eis(f_start=1e5, f_end=0.1)]))
        assert not _has_error(result, "PV005")


# ---------------------------------------------------------------------------
# PV006: EIS f_start > 10 MHz
# ---------------------------------------------------------------------------


class TestPV006:
    """PV006: EIS f_start max 10 MHz."""

    def test_f_start_exceeds_10MHz_fails(self):
        result = validate_electrochemistry(_ir(steps=[_eis(f_start=11e6)]))
        assert _has_error(result, "PV006")

    def test_f_start_at_10MHz_passes(self):
        result = validate_electrochemistry(_ir(steps=[_eis(f_start=10e6)]))
        assert not _has_error(result, "PV006")


# ---------------------------------------------------------------------------
# PV007: EIS f_end < 1e-6 Hz
# ---------------------------------------------------------------------------


class TestPV007:
    """PV007: EIS f_end minimum 1e-6 Hz."""

    def test_f_end_below_1uHz_fails(self):
        result = validate_electrochemistry(_ir(steps=[_eis(f_end=1e-7)]))
        assert _has_error(result, "PV007")

    def test_f_end_at_1uHz_passes(self):
        result = validate_electrochemistry(_ir(steps=[_eis(f_end=1e-6)]))
        assert not _has_error(result, "PV007")


# ---------------------------------------------------------------------------
# PV008: EIS amplitude <= 0
# ---------------------------------------------------------------------------


class TestPV008:
    """PV008: EIS amplitude must be > 0."""

    @pytest.mark.parametrize("amp", [0.0, -0.005])
    def test_non_positive_amplitude_fails(self, amp):
        result = validate_electrochemistry(_ir(steps=[_eis(amplitude=amp)]))
        assert _has_error(result, "PV008")

    def test_positive_amplitude_passes(self):
        result = validate_electrochemistry(_ir(steps=[_eis(amplitude=0.01)]))
        assert not _has_error(result, "PV008")


# ---------------------------------------------------------------------------
# PV009: EIS amplitude > 0.1 V
# ---------------------------------------------------------------------------


class TestPV009:
    """PV009: EIS amplitude max 0.1 V."""

    def test_amplitude_exceeds_max_fails(self):
        result = validate_electrochemistry(_ir(steps=[_eis(amplitude=0.2)]))
        assert _has_error(result, "PV009")

    def test_amplitude_at_max_passes(self):
        result = validate_electrochemistry(_ir(steps=[_eis(amplitude=0.1)]))
        assert not _has_error(result, "PV009")

    def test_amplitude_below_max_passes(self):
        result = validate_electrochemistry(_ir(steps=[_eis(amplitude=0.005)]))
        assert not _has_error(result, "PV009")


# ---------------------------------------------------------------------------
# PV010: potential outside +/-10 V
# ---------------------------------------------------------------------------


class TestPV010:
    """PV010: All potentials must be in [-10, 10] V."""

    @pytest.mark.parametrize(
        "field, value",
        [
            ("vertex1", 11.0),
            ("vertex2", -11.0),
            ("potential", 15.0),
            ("e_start", -12.0),
            ("e_end", 10.5),
        ],
    )
    def test_out_of_range_potential_fails(self, field, value):
        step = IRStep(technique="cv", **{field: value})
        result = validate_electrochemistry(_ir(steps=[step]))
        assert _has_error(result, "PV010")

    def test_in_range_potentials_pass(self):
        result = validate_electrochemistry(
            _ir(steps=[_cv(vertex1=-5.0, vertex2=5.0)])
        )
        assert not _has_error(result, "PV010")

    def test_boundary_potentials_pass(self):
        result = validate_electrochemistry(
            _ir(steps=[_cv(vertex1=-10.0, vertex2=10.0)])
        )
        assert not _has_error(result, "PV010")


# ---------------------------------------------------------------------------
# PV011: hold duration <= 0
# ---------------------------------------------------------------------------


class TestPV011:
    """PV011: Hold duration must be > 0."""

    @pytest.mark.parametrize("dur", [0.0, -1.0, -100.0])
    def test_non_positive_hold_duration_fails(self, dur):
        result = validate_electrochemistry(_ir(steps=[_hold(duration=dur)]))
        assert _has_error(result, "PV011")

    def test_positive_hold_duration_passes(self):
        result = validate_electrochemistry(_ir(steps=[_hold(duration=10.0)]))
        assert not _has_error(result, "PV011")


# ---------------------------------------------------------------------------
# PV012 / PV013: loop count
# ---------------------------------------------------------------------------


class TestPV012:
    """PV012: Loop count must be > 0."""

    @pytest.mark.parametrize("count", [0, -1, -100])
    def test_non_positive_loop_count_fails(self, count):
        loop = IRLoop(count=count, steps=[_cv()])
        result = validate_electrochemistry(_ir(loop=loop))
        assert _has_error(result, "PV012")

    def test_positive_loop_count_passes(self):
        loop = IRLoop(count=1, steps=[_cv()])
        result = validate_electrochemistry(_ir(loop=loop))
        assert not _has_error(result, "PV012")


class TestPV013:
    """PV013: Loop count must be <= 1000000."""

    def test_exceeds_max_loop_count_fails(self):
        loop = IRLoop(count=1_000_001, steps=[_cv()])
        result = validate_electrochemistry(_ir(loop=loop))
        assert _has_error(result, "PV013")

    def test_at_max_loop_count_passes(self):
        loop = IRLoop(count=1_000_000, steps=[_cv()])
        result = validate_electrochemistry(_ir(loop=loop))
        assert not _has_error(result, "PV013")

    def test_variable_count_skipped(self):
        """String-based loop count (variable reference) skips numeric checks."""
        loop = IRLoop(count="{n_cycles}", steps=[_cv()])
        result = validate_electrochemistry(_ir(loop=loop))
        assert not _has_error(result, "PV012")
        assert not _has_error(result, "PV013")


# ---------------------------------------------------------------------------
# Valid CV passes all PV rules
# ---------------------------------------------------------------------------


class TestValidCVPassesAll:
    """A well-formed CV step should produce no errors."""

    def test_standard_cv_no_errors(self):
        result = validate_electrochemistry(_ir(steps=[_cv()]))
        assert len(result.errors) == 0

    def test_standard_eis_no_errors(self):
        result = validate_electrochemistry(_ir(steps=[_eis()]))
        assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# DR warnings
# ---------------------------------------------------------------------------


class TestDRWarnings:
    """Domain-rule warnings (DR codes)."""

    def test_dr004_short_ocp_duration(self):
        """OCP < 30 s triggers DR004 warning."""
        result = validate_electrochemistry(_ir(steps=[_ocp(duration=10.0)]))
        assert _has_warning(result, "DR004")

    def test_dr004_adequate_ocp_no_warning(self):
        result = validate_electrochemistry(_ir(steps=[_ocp(duration=60.0)]))
        assert not _has_warning(result, "DR004")

    def test_dr005_high_eis_amplitude(self):
        """EIS amplitude > 0.01 V triggers DR005 warning."""
        result = validate_electrochemistry(_ir(steps=[_eis(amplitude=0.05)]))
        assert _has_warning(result, "DR005")

    def test_dr005_low_eis_amplitude_no_warning(self):
        result = validate_electrochemistry(_ir(steps=[_eis(amplitude=0.005)]))
        assert not _has_warning(result, "DR005")

    def test_dr011_low_cv_cycles(self):
        """CV cycles < 3 triggers DR011 warning."""
        result = validate_electrochemistry(_ir(steps=[_cv(cycles=1)]))
        assert _has_warning(result, "DR011")

    def test_dr011_enough_cv_cycles_no_warning(self):
        result = validate_electrochemistry(_ir(steps=[_cv(cycles=5)]))
        assert not _has_warning(result, "DR011")

    def test_warnings_do_not_make_result_invalid(self):
        """Warnings should not set valid=False."""
        result = validate_electrochemistry(_ir(steps=[_ocp(duration=5.0)]))
        assert result.valid is True
        assert len(result.warnings) > 0


# ---------------------------------------------------------------------------
# Rule registry enable/disable
# ---------------------------------------------------------------------------


class TestRuleRegistry:
    """Rule registry enable/disable controls."""

    def test_disable_rule(self):
        """Disabled rule should not fire."""
        registry = get_registry()
        registry.disable("PV001")
        try:
            result = validate_electrochemistry(_ir(steps=[_cv(scan_rate=50.0)]))
            assert not _has_error(result, "PV001")
        finally:
            registry.enable("PV001")

    def test_re_enable_rule(self):
        """Re-enabled rule fires again."""
        registry = get_registry()
        registry.disable("PV001")
        registry.enable("PV001")
        result = validate_electrochemistry(_ir(steps=[_cv(scan_rate=50.0)]))
        assert _has_error(result, "PV001")

    def test_disable_all(self):
        """disable_all suppresses all rules."""
        registry = get_registry()
        registry.disable_all()
        try:
            result = validate_electrochemistry(
                _ir(steps=[_cv(scan_rate=50.0, cycles=-1, vertex1=0.5, vertex2=0.5)])
            )
            assert len(result.errors) == 0
        finally:
            registry.enable_all()

    def test_enable_all(self):
        """enable_all restores all rules."""
        registry = get_registry()
        registry.disable_all()
        registry.enable_all()
        result = validate_electrochemistry(_ir(steps=[_cv(scan_rate=50.0)]))
        assert _has_error(result, "PV001")

    def test_registry_has_pv_rules(self):
        registry = get_registry()
        rules = registry.rules
        for code in ["PV001", "PV002", "PV003", "PV004", "PV005",
                      "PV006", "PV007", "PV008", "PV009", "PV010", "PV011"]:
            assert code in rules, f"Expected rule {code} in registry"

    def test_registry_has_dr_rules(self):
        registry = get_registry()
        rules = registry.rules
        for code in ["DR004", "DR005", "DR011"]:
            assert code in rules, f"Expected rule {code} in registry"


# ---------------------------------------------------------------------------
# Multiple errors on same step
# ---------------------------------------------------------------------------


class TestMultipleErrors:
    """A single badly-formed step can produce multiple errors."""

    def test_cv_with_multiple_violations(self):
        step = _cv(scan_rate=50.0, cycles=-1, vertex1=0.5, vertex2=0.5)
        result = validate_electrochemistry(_ir(steps=[step]))
        codes = {i.code for i in result.errors}
        assert "PV001" in codes
        assert "PV003" in codes
        assert "PV004" in codes

    def test_eis_with_multiple_violations(self):
        step = _eis(f_start=0.01, f_end=1e5, amplitude=-0.01)
        result = validate_electrochemistry(_ir(steps=[step]))
        codes = {i.code for i in result.errors}
        assert "PV005" in codes
        assert "PV008" in codes
