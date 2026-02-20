"""Tests for ecproc.validator.syntax -- L1 structural validation."""

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
from ecproc.validator.syntax import VALID_TECHNIQUES, validate_syntax

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)


def _meta(**overrides) -> IRMetadata:
    defaults = dict(
        protocol="test",
        version="1.0",
        created=_NOW,
        ecproc_version="0.1.0",
        source_hash="sha256:abc",
    )
    defaults.update(overrides)
    return IRMetadata(**defaults)


def _prov() -> IRProvenance:
    return IRProvenance(source_file=None, source_hash="sha256:abc", parser_version="0.1.0")


def _system(**overrides) -> IRSystem:
    defaults = dict(electrodes=3, reference="RHE")
    defaults.update(overrides)
    return IRSystem(**defaults)


def _cv_step(**extra) -> IRStep:
    return IRStep(technique="cv", scan_rate=0.05, vertex1=0.05, vertex2=1.2, cycles=3, **extra)


def _phase(name="activation", steps=None) -> IRPhase:
    return IRPhase(name=name, steps=steps or [_cv_step()])


def _ir(
    metadata=None, system=None, procedure=None, **kw
) -> FaradayIR:
    return FaradayIR(
        metadata=metadata or _meta(),
        system=system or _system(),
        procedure=procedure if procedure is not None else [_phase()],
        provenance=_prov(),
        **kw,
    )


# ---------------------------------------------------------------------------
# Tests: valid IR passes
# ---------------------------------------------------------------------------


class TestValidIR:
    """Minimal valid IR should pass L1 with no issues."""

    def test_valid_ir_passes(self):
        result = validate_syntax(_ir())
        assert result.valid is True
        assert len(result.errors) == 0

    def test_valid_ir_no_warnings(self):
        result = validate_syntax(_ir())
        assert len(result.warnings) == 0

    def test_multiple_phases_valid(self):
        ir = _ir(procedure=[_phase("p1"), _phase("p2")])
        result = validate_syntax(ir)
        assert result.valid is True

    def test_all_valid_techniques_pass(self):
        for tech in VALID_TECHNIQUES:
            step = IRStep(technique=tech)
            ir = _ir(procedure=[_phase(steps=[step])])
            result = validate_syntax(ir)
            assert result.valid is True, f"Technique '{tech}' should be valid"


# ---------------------------------------------------------------------------
# Tests: metadata failures
# ---------------------------------------------------------------------------


class TestMetadataErrors:
    """Missing metadata fields trigger SYN001/SYN002."""

    def test_empty_protocol_fails(self):
        ir = _ir(metadata=_meta(protocol=""))
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN001" in codes

    def test_empty_version_fails(self):
        ir = _ir(metadata=_meta(version=""))
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN002" in codes


# ---------------------------------------------------------------------------
# Tests: system failures
# ---------------------------------------------------------------------------


class TestSystemErrors:
    """System validation: electrode count, reference."""

    @pytest.mark.parametrize("elec", [0, 1, 4, -1])
    def test_invalid_electrode_count(self, elec):
        ir = _ir(system=_system(electrodes=elec))
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN003" in codes

    @pytest.mark.parametrize("elec", [2, 3])
    def test_valid_electrode_count(self, elec):
        ir = _ir(system=_system(electrodes=elec))
        result = validate_syntax(ir)
        codes = [i.code for i in result.errors]
        assert "SYN003" not in codes

    def test_empty_reference_fails(self):
        ir = _ir(system=_system(reference=""))
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN004" in codes


# ---------------------------------------------------------------------------
# Tests: procedure failures
# ---------------------------------------------------------------------------


class TestProcedureErrors:
    """Empty procedure, empty phase, empty step technique."""

    def test_empty_procedure_fails(self):
        ir = _ir(procedure=[])
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN005" in codes

    def test_phase_no_name_fails(self):
        phase = IRPhase(name="", steps=[_cv_step()])
        ir = _ir(procedure=[phase])
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN006" in codes

    def test_phase_no_steps_fails(self):
        phase = IRPhase(name="empty", steps=[])
        ir = _ir(procedure=[phase])
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN007" in codes


# ---------------------------------------------------------------------------
# Tests: technique validation
# ---------------------------------------------------------------------------


class TestTechniqueValidation:
    """Unknown and missing technique names."""

    def test_empty_technique_fails(self):
        step = IRStep(technique="")
        ir = _ir(procedure=[_phase(steps=[step])])
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN008" in codes

    @pytest.mark.parametrize("tech", ["unknown", "xrd", "sem", "INVALID", "cv2"])
    def test_unknown_technique_fails(self, tech):
        step = IRStep(technique=tech)
        ir = _ir(procedure=[_phase(steps=[step])])
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN009" in codes

    def test_error_includes_technique_name(self):
        step = IRStep(technique="foo")
        ir = _ir(procedure=[_phase(steps=[step])])
        result = validate_syntax(ir)
        msg = result.errors[0].message
        assert "foo" in msg


# ---------------------------------------------------------------------------
# Tests: loop validation
# ---------------------------------------------------------------------------


class TestLoopValidation:
    """Loops within phases."""

    def test_valid_loop_passes(self):
        loop = IRLoop(count=10, steps=[_cv_step()])
        ir = _ir(procedure=[_phase(steps=[loop])])
        result = validate_syntax(ir)
        assert result.valid

    def test_empty_loop_fails(self):
        loop = IRLoop(count=5, steps=[])
        ir = _ir(procedure=[_phase(steps=[loop])])
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN010" in codes

    def test_loop_with_unknown_technique_fails(self):
        step = IRStep(technique="bogus")
        loop = IRLoop(count=3, steps=[step])
        ir = _ir(procedure=[_phase(steps=[loop])])
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN009" in codes

    def test_nested_loop_validated(self):
        inner = IRLoop(count=2, steps=[])
        outer = IRLoop(count=5, steps=[inner])
        ir = _ir(procedure=[_phase(steps=[outer])])
        result = validate_syntax(ir)
        assert not result.valid
        codes = [i.code for i in result.errors]
        assert "SYN010" in codes


# ---------------------------------------------------------------------------
# Tests: error path information
# ---------------------------------------------------------------------------


class TestErrorPaths:
    """Verify that error paths point to the right location."""

    def test_procedure_path(self):
        ir = _ir(procedure=[])
        result = validate_syntax(ir)
        assert any(i.path == "procedure" for i in result.errors)

    def test_step_technique_path(self):
        step = IRStep(technique="xrd")
        ir = _ir(procedure=[_phase(steps=[step])])
        result = validate_syntax(ir)
        assert any("technique" in (i.path or "") for i in result.errors)

    def test_second_phase_index(self):
        good_phase = _phase("good")
        bad_phase = IRPhase(name="", steps=[_cv_step()])
        ir = _ir(procedure=[good_phase, bad_phase])
        result = validate_syntax(ir)
        assert any("procedure[1]" in (i.path or "") for i in result.errors)
