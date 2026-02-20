"""Tests for ecproc.ir.generator -- AST to Faraday IR transformation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ecproc._version import __version__
from ecproc.ir.generator import generate_ir
from ecproc.ir.schema import (
    FaradayIR,
    IRElectrolyte,
    IRStep,
)
from ecproc.parser.ast import (
    ElectrolyteAST,
    LoopAST,
    MetadataAST,
    OutputAST,
    PhaseAST,
    ProcedureAST,
    ReferenceMonitorAST,
    SafetyAST,
    StepAST,
    SystemAST,
    ThermalRunawayAST,
    WorkingElectrodeAST,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_metadata(**overrides) -> MetadataAST:
    defaults = dict(protocol="test-protocol", version="1.0", author="tester")
    defaults.update(overrides)
    return MetadataAST(**defaults)


def _make_system(**overrides) -> SystemAST:
    defaults = dict(electrodes=3, reference="RHE")
    defaults.update(overrides)
    return SystemAST(**defaults)


def _make_cv_step(**overrides) -> StepAST:
    defaults = dict(
        technique="cv",
        parameters={
            "scan_rate": "50 mV/s",
            "vertex1": "0.05 V",
            "vertex2": "1.2 V",
            "cycles": 3,
        },
    )
    defaults.update(overrides)
    return StepAST(**defaults)


def _make_eis_step(**overrides) -> StepAST:
    defaults = dict(
        technique="eis",
        parameters={
            "f_start": "100 kHz",
            "f_end": "100 mHz",
            "amplitude": "10 mV",
        },
    )
    defaults.update(overrides)
    return StepAST(**defaults)


def _make_phase(name: str = "activation", steps=None) -> PhaseAST:
    if steps is None:
        steps = [_make_cv_step()]
    return PhaseAST(name=name, steps=steps)


def _make_ast(
    phases=None,
    safety=None,
    system=None,
    metadata=None,
    output=None,
    **kw,
) -> ProcedureAST:
    return ProcedureAST(
        metadata=metadata or _make_metadata(),
        system=system or _make_system(),
        procedure=phases or [_make_phase()],
        safety=safety,
        output=output,
        **kw,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateIRBasic:
    """Basic round-trip and structure tests."""

    def test_returns_faraday_ir(self):
        ir = generate_ir(_make_ast())
        assert isinstance(ir, FaradayIR)

    def test_faraday_version_default(self):
        ir = generate_ir(_make_ast())
        assert ir.faraday_version == "1.0"

    def test_procedure_has_one_phase(self):
        ir = generate_ir(_make_ast())
        assert len(ir.procedure) == 1
        assert ir.procedure[0].name == "activation"

    def test_phase_has_one_step(self):
        ir = generate_ir(_make_ast())
        step = ir.procedure[0].steps[0]
        assert isinstance(step, IRStep)
        assert step.technique == "cv"

    def test_multiple_phases_preserved(self):
        p1 = _make_phase("conditioning")
        p2 = _make_phase("measurement")
        ir = generate_ir(_make_ast(phases=[p1, p2]))
        assert len(ir.procedure) == 2
        assert ir.procedure[0].name == "conditioning"
        assert ir.procedure[1].name == "measurement"


class TestMetadata:
    """Metadata fields populated correctly."""

    def test_protocol_populated(self):
        ir = generate_ir(_make_ast())
        assert ir.metadata.protocol == "test-protocol"

    def test_version_populated(self):
        ir = generate_ir(_make_ast())
        assert ir.metadata.version == "1.0"

    def test_ecproc_version(self):
        ir = generate_ir(_make_ast())
        assert ir.metadata.ecproc_version == __version__

    def test_created_is_recent(self):
        before = datetime.now(timezone.utc)
        ir = generate_ir(_make_ast())
        after = datetime.now(timezone.utc)
        assert before <= ir.metadata.created <= after

    def test_author_populated(self):
        ir = generate_ir(_make_ast(metadata=_make_metadata(author="Alice")))
        assert ir.metadata.author == "Alice"


class TestProvenance:
    """Source hash and provenance fields."""

    def test_source_hash_is_sha256(self):
        ir = generate_ir(_make_ast())
        assert ir.provenance.source_hash.startswith("sha256:")

    def test_provenance_parser_version(self):
        ir = generate_ir(_make_ast())
        assert ir.provenance.parser_version == __version__

    def test_metadata_source_hash_matches_provenance(self):
        ir = generate_ir(_make_ast())
        assert ir.metadata.source_hash == ir.provenance.source_hash


class TestUnitNormalization:
    """Verify all unit conversions at the AST -> IR boundary."""

    def test_scan_rate_mV_s_to_V_s(self):
        """50 mV/s -> 0.05 V/s."""
        ir = generate_ir(_make_ast())
        step = ir.procedure[0].steps[0]
        extras = step.model_dump(exclude=set(IRStep.model_fields.keys()))
        assert extras["scan_rate"] == pytest.approx(0.05)

    def test_vertex_V_unchanged(self):
        """Potential in V stays unchanged."""
        ir = generate_ir(_make_ast())
        step = ir.procedure[0].steps[0]
        extras = step.model_dump(exclude=set(IRStep.model_fields.keys()))
        assert extras["vertex1"] == pytest.approx(0.05)
        assert extras["vertex2"] == pytest.approx(1.2)

    def test_cycles_int_unchanged(self):
        """Integer cycles pass through unchanged."""
        ir = generate_ir(_make_ast())
        step = ir.procedure[0].steps[0]
        extras = step.model_dump(exclude=set(IRStep.model_fields.keys()))
        assert extras["cycles"] == 3

    @pytest.mark.parametrize(
        "input_val, expected_si",
        [
            ("100 kHz", 100_000.0),
            ("100 mHz", 0.1),
            ("10 mV", 0.01),
        ],
        ids=["kHz_to_Hz", "mHz_to_Hz", "mV_to_V"],
    )
    def test_eis_param_normalization(self, input_val, expected_si):
        """EIS frequency and amplitude normalized to SI."""
        # Build a single-param step so we can isolate the conversion
        step_ast = StepAST(
            technique="eis",
            parameters={"param": input_val},
        )
        phase = _make_phase(steps=[step_ast])
        ir = generate_ir(_make_ast(phases=[phase]))
        extras = ir.procedure[0].steps[0].model_dump(
            exclude=set(IRStep.model_fields.keys())
        )
        assert extras["param"] == pytest.approx(expected_si)

    def test_eis_step_full(self):
        """Full EIS step: f_start=100kHz->1e5, f_end=100mHz->0.1, amplitude=10mV->0.01."""
        phase = _make_phase(steps=[_make_eis_step()])
        ir = generate_ir(_make_ast(phases=[phase]))
        step = ir.procedure[0].steps[0]
        extras = step.model_dump(exclude=set(IRStep.model_fields.keys()))
        assert extras["f_start"] == pytest.approx(1e5)
        assert extras["f_end"] == pytest.approx(0.1)
        assert extras["amplitude"] == pytest.approx(0.01)


class TestWorkingElectrodeConversion:
    """Working electrode area and loading conversions."""

    def test_area_cm2_to_m2(self):
        """1 cm2 -> 1e-4 m2."""
        sys = _make_system(
            working=WorkingElectrodeAST(material="IrO2", area_cm2=1.0)
        )
        ir = generate_ir(_make_ast(system=sys))
        assert ir.system.working is not None
        assert ir.system.working.area_m2 == pytest.approx(1e-4)

    def test_loading_ug_cm2_to_kg_m2(self):
        """200 ug/cm2 -> 200e-5 kg/m2 = 2e-3."""
        sys = _make_system(
            working=WorkingElectrodeAST(
                material="IrO2", loading_ug_cm2=200.0
            )
        )
        ir = generate_ir(_make_ast(system=sys))
        assert ir.system.working is not None
        assert ir.system.working.loading_kg_m2 == pytest.approx(200.0 * 1e-5)

    def test_no_working_electrode(self):
        ir = generate_ir(_make_ast(system=_make_system(working=None)))
        assert ir.system.working is None


class TestElectrolyteConversion:
    """Electrolyte concentration conversion."""

    def test_M_to_mol_m3(self):
        """0.5 M -> 500 mol/m3."""
        sys = _make_system(
            electrolyte=ElectrolyteAST(solute="H2SO4", concentration_M=0.5)
        )
        ir = generate_ir(_make_ast(system=sys))
        assert isinstance(ir.system.electrolyte, IRElectrolyte)
        assert ir.system.electrolyte.concentration_mol_m3 == pytest.approx(500.0)

    def test_string_electrolyte_passthrough(self):
        sys = _make_system(electrolyte="0.1 M HClO4")
        ir = generate_ir(_make_ast(system=sys))
        assert ir.system.electrolyte == "0.1 M HClO4"


class TestPhaseSetupTeardown:
    """Phase setup/teardown preserved in IR."""

    def test_setup_preserved(self):
        phase = PhaseAST(
            name="cond",
            setup={"purge_gas": "N2", "purge_time_min": 10},
            steps=[_make_cv_step()],
        )
        ir = generate_ir(_make_ast(phases=[phase]))
        assert ir.procedure[0].setup == {"purge_gas": "N2", "purge_time_min": 10}

    def test_teardown_preserved(self):
        phase = PhaseAST(
            name="cond",
            steps=[_make_cv_step()],
            teardown={"rinse": True},
        )
        ir = generate_ir(_make_ast(phases=[phase]))
        assert ir.procedure[0].teardown == {"rinse": True}

    def test_stabilize_preserved(self):
        phase = PhaseAST(
            name="cond",
            steps=[_make_cv_step()],
            stabilize=["temperature", "ocp"],
        )
        ir = generate_ir(_make_ast(phases=[phase]))
        assert ir.procedure[0].stabilize == ["temperature", "ocp"]


class TestSafetyNormalization:
    """Safety field normalization."""

    def test_max_current_mA_to_A(self):
        safety = SafetyAST(max_current="100 mA")
        ir = generate_ir(_make_ast(safety=safety))
        assert ir.safety is not None
        assert ir.safety.max_current_A == pytest.approx(0.1)

    def test_voltage_window_V(self):
        safety = SafetyAST(voltage_window=["0.0 V", "1.8 V"])
        ir = generate_ir(_make_ast(safety=safety))
        assert ir.safety is not None
        assert ir.safety.voltage_window_V == pytest.approx((0.0, 1.8))

    def test_temperature_limits(self):
        safety = SafetyAST(temperature_limits=["10 C", "60 C"])
        ir = generate_ir(_make_ast(safety=safety))
        assert ir.safety is not None
        assert ir.safety.temperature_limits_C == pytest.approx((10.0, 60.0))

    def test_thermal_runaway_C_min_to_K_s(self):
        """60 C/min -> 1.0 K/s."""
        safety = SafetyAST(
            thermal_runaway=ThermalRunawayAST(max_dT_dt=60.0, action="cell_off")
        )
        ir = generate_ir(_make_ast(safety=safety))
        assert ir.safety is not None
        assert ir.safety.thermal_runaway is not None
        assert ir.safety.thermal_runaway.max_dT_dt_K_s == pytest.approx(1.0)

    def test_reference_monitor(self):
        safety = SafetyAST(
            reference_electrode_monitor=ReferenceMonitorAST(
                max_Ru_change="10x",
                max_ocp_drift="500 mV/s",
                action="cell_off",
            )
        )
        ir = generate_ir(_make_ast(safety=safety))
        assert ir.safety is not None
        rm = ir.safety.reference_electrode_monitor
        assert rm is not None
        assert rm.max_Ru_change_factor == pytest.approx(10.0)
        assert rm.max_ocp_drift_V_s == pytest.approx(0.5)

    def test_no_safety_block(self):
        ir = generate_ir(_make_ast(safety=None))
        assert ir.safety is None


class TestVariablesCollection:
    """Extract fields collected into IRVariables."""

    def test_extract_string(self):
        step = StepAST(
            technique="eis",
            parameters={"f_start": "100 kHz", "f_end": "100 mHz"},
            tag="eis_initial",
            extract="Ru",
        )
        ir = generate_ir(_make_ast(phases=[_make_phase(steps=[step])]))
        assert ir.variables is not None
        assert "eis_initial" in ir.variables.extractions
        assert ir.variables.extractions["eis_initial"] == "Ru"

    def test_extract_dict(self):
        step = StepAST(
            technique="eis",
            parameters={},
            tag="eis1",
            extract={"Ru": "fit.Rs", "Cdl": "fit.Cdl"},
        )
        ir = generate_ir(_make_ast(phases=[_make_phase(steps=[step])]))
        assert ir.variables is not None
        assert "eis1.Ru" in ir.variables.extractions
        assert "eis1.Cdl" in ir.variables.extractions

    def test_no_extract_returns_none(self):
        ir = generate_ir(_make_ast())
        # Default CV step has no extract field
        assert ir.variables is None

    def test_tag_fallback_to_technique(self):
        step = StepAST(
            technique="eis",
            parameters={},
            extract="Ru",
        )
        ir = generate_ir(_make_ast(phases=[_make_phase(steps=[step])]))
        assert ir.variables is not None
        assert "eis" in ir.variables.extractions


class TestLoopConversion:
    """Loop steps are converted properly."""

    def test_loop_preserves_count(self):
        loop = LoopAST(count=10, steps=[_make_cv_step()])
        phase = PhaseAST(name="cycling", steps=[loop])
        ir = generate_ir(_make_ast(phases=[phase]))
        from ecproc.ir.schema import IRLoop
        assert isinstance(ir.procedure[0].steps[0], IRLoop)
        assert ir.procedure[0].steps[0].count == 10

    def test_loop_steps_normalized(self):
        step = StepAST(
            technique="cv",
            parameters={"scan_rate": "100 mV/s"},
        )
        loop = LoopAST(count=5, steps=[step])
        phase = PhaseAST(name="cycling", steps=[loop])
        ir = generate_ir(_make_ast(phases=[phase]))
        from ecproc.ir.schema import IRLoop
        loop_ir = ir.procedure[0].steps[0]
        assert isinstance(loop_ir, IRLoop)
        inner = loop_ir.steps[0]
        extras = inner.model_dump(exclude=set(IRStep.model_fields.keys()))
        assert extras["scan_rate"] == pytest.approx(0.1)

    def test_nested_loop(self):
        inner_loop = LoopAST(count=3, steps=[_make_cv_step()])
        outer_loop = LoopAST(count=5, steps=[inner_loop])
        phase = PhaseAST(name="nesting", steps=[outer_loop])
        ir = generate_ir(_make_ast(phases=[phase]))
        from ecproc.ir.schema import IRLoop
        outer = ir.procedure[0].steps[0]
        assert isinstance(outer, IRLoop)
        assert outer.count == 5
        inner = outer.steps[0]
        assert isinstance(inner, IRLoop)
        assert inner.count == 3


class TestOutputBlock:
    """Output block passthrough."""

    def test_output_ecdl_preserved(self):
        output = OutputAST(ecdl={"format": "ecdl-v1", "bucket": "s3://data"})
        ir = generate_ir(_make_ast(output=output))
        assert ir.output is not None
        assert ir.output.ecdl["format"] == "ecdl-v1"

    def test_no_output(self):
        ir = generate_ir(_make_ast(output=None))
        assert ir.output is None
