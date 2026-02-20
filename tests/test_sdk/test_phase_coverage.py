"""Tests for ecproc.sdk.phase — coverage of all Phase technique methods."""

from __future__ import annotations

from ecproc.parser.ast import LoopAST, PhaseAST
from ecproc.sdk.phase import Loop, Phase

# ---------------------------------------------------------------------------
# Phase technique methods
# ---------------------------------------------------------------------------


class TestPhaseTechniques:
    """Each technique method should add a StepAST with the correct technique name."""

    def test_lsv(self):
        phase = Phase("test")
        phase.lsv(start="0 V", stop="1.0 V", rate="10 mV/s")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "lsv"
        assert ast.steps[0].parameters["start"] == "0 V"

    def test_ocp(self):
        phase = Phase("test")
        phase.ocp(duration="30 s")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "ocp"
        assert ast.steps[0].parameters["duration"] == "30 s"

    def test_hold(self):
        phase = Phase("test")
        phase.hold(potential="0.5 V", duration="60 s")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "hold"
        assert ast.steps[0].parameters["potential"] == "0.5 V"

    def test_galvanostatic(self):
        phase = Phase("test")
        phase.galvanostatic(current="10 mA", duration="120 s")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "galvanostatic"
        assert ast.steps[0].parameters["current"] == "10 mA"

    def test_dpv(self):
        phase = Phase("test")
        phase.dpv(start="0 V", stop="1.0 V")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "dpv"

    def test_swv(self):
        phase = Phase("test")
        phase.swv(start="0 V", stop="1.0 V", frequency="25 Hz")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "swv"
        assert ast.steps[0].parameters["frequency"] == "25 Hz"

    def test_gcd(self):
        phase = Phase("test")
        phase.gcd(current="5 mA", voltage_window="0 V and 1 V")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "gcd"

    def test_cc(self):
        phase = Phase("test")
        phase.cc(current="1 mA", duration="300 s")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "cc"

    def test_stripping(self):
        phase = Phase("test")
        phase.stripping(deposition_potential="-0.5 V", deposition_time="30 s")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "stripping"
        assert ast.steps[0].parameters["deposition_potential"] == "-0.5 V"

    def test_purge(self):
        phase = Phase("test")
        phase.purge(gas="N2", duration="10 min")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "purge"
        assert ast.steps[0].parameters["gas"] == "N2"


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


class TestPhaseEnvironmentHelpers:
    """Tests for gas() and rotation() setup helpers."""

    def test_gas_sets_setup(self):
        phase = Phase("test")
        phase.gas("N2")
        ast = phase.to_ast()
        assert ast.setup is not None
        assert ast.setup["gas"] == "N2"

    def test_gas_when_setup_already_exists(self):
        phase = Phase("test")
        phase.setup(temperature="25 C")
        phase.gas("O2")
        ast = phase.to_ast()
        assert ast.setup["gas"] == "O2"
        assert ast.setup["temperature"] == "25 C"

    def test_rotation_sets_rpm(self):
        phase = Phase("test")
        phase.rotation(1600)
        ast = phase.to_ast()
        assert ast.setup is not None
        assert ast.setup["rotation"] == 1600

    def test_rotation_when_setup_already_exists(self):
        phase = Phase("test")
        phase.setup(temperature="25 C")
        phase.rotation(900)
        ast = phase.to_ast()
        assert ast.setup["rotation"] == 900
        assert ast.setup["temperature"] == "25 C"


# ---------------------------------------------------------------------------
# Logging and computation steps
# ---------------------------------------------------------------------------


class TestPhaseLogAndCompute:
    """Tests for log() and compute() methods."""

    def test_log_adds_step(self):
        phase = Phase("test")
        phase.log("Starting measurement")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "log"
        assert ast.steps[0].parameters["message"] == "Starting measurement"

    def test_compute_adds_step(self):
        phase = Phase("test")
        phase.compute("tafel_slope", "dE / d(log(i))")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "compute"
        assert ast.steps[0].parameters["name"] == "tafel_slope"
        assert ast.steps[0].parameters["expression"] == "dE / d(log(i))"


# ---------------------------------------------------------------------------
# Phase AST generation
# ---------------------------------------------------------------------------


class TestPhaseToAST:
    """Tests for Phase.to_ast() output structure."""

    def test_name_is_set(self):
        phase = Phase("Conditioning")
        ast = phase.to_ast()
        assert isinstance(ast, PhaseAST)
        assert ast.name == "Conditioning"

    def test_empty_phase_has_no_steps(self):
        phase = Phase("empty")
        ast = phase.to_ast()
        assert ast.steps == []

    def test_multiple_steps(self):
        phase = Phase("multi")
        phase.cv(rate="50 mV/s")
        phase.eis(frequency="1 kHz")
        phase.ocp(duration="10 s")
        ast = phase.to_ast()
        assert len(ast.steps) == 3
        assert ast.steps[0].technique == "cv"
        assert ast.steps[1].technique == "eis"
        assert ast.steps[2].technique == "ocp"

    def test_setup_and_teardown(self):
        phase = Phase("full")
        phase.setup(temperature="25 C")
        phase.teardown(purge="N2")
        ast = phase.to_ast()
        assert ast.setup == {"temperature": "25 C"}
        assert ast.teardown == {"purge": "N2"}

    def test_stabilize(self):
        phase = Phase("stab")
        phase.stabilize("ocp < 1 mV/s", "temperature == 25 C")
        ast = phase.to_ast()
        assert ast.stabilize == ["ocp < 1 mV/s", "temperature == 25 C"]

    def test_tag_and_extract(self):
        phase = Phase("tagged")
        phase.cv(rate="50 mV/s", tag="cv_conditioning", extract="peak_current")
        ast = phase.to_ast()
        assert ast.steps[0].tag == "cv_conditioning"
        assert ast.steps[0].extract == "peak_current"

    def test_vendor_flags(self):
        phase = Phase("vendor")
        phase.cv(rate="50 mV/s", vendor_flags={"biologic": {"bandwidth": 5}})
        ast = phase.to_ast()
        assert ast.steps[0].vendor_flags == {"biologic": {"bandwidth": 5}}


# ---------------------------------------------------------------------------
# Loop builder
# ---------------------------------------------------------------------------


class TestLoopBuilder:
    """Tests for the Loop class and its technique methods."""

    def test_loop_techniques(self):
        lp = Loop(5)
        lp.cv(rate="50 mV/s").eis(frequency="1 kHz")
        ast = lp.to_ast()
        assert isinstance(ast, LoopAST)
        assert ast.count == 5
        assert len(ast.steps) == 2
        assert ast.steps[0].technique == "cv"
        assert ast.steps[1].technique == "eis"

    def test_loop_stop_if(self):
        lp = Loop(10, stop_if="current < 1 mA")
        ast = lp.to_ast()
        assert ast.stop_if == "current < 1 mA"

    def test_loop_lsv(self):
        lp = Loop(3)
        lp.lsv(rate="10 mV/s")
        ast = lp.to_ast()
        assert ast.steps[0].technique == "lsv"

    def test_loop_ocp(self):
        lp = Loop(3)
        lp.ocp(duration="30 s")
        ast = lp.to_ast()
        assert ast.steps[0].technique == "ocp"

    def test_loop_hold(self):
        lp = Loop(3)
        lp.hold(potential="0.5 V")
        ast = lp.to_ast()
        assert ast.steps[0].technique == "hold"

    def test_loop_galvanostatic(self):
        lp = Loop(3)
        lp.galvanostatic(current="10 mA")
        ast = lp.to_ast()
        assert ast.steps[0].technique == "galvanostatic"

    def test_loop_dpv(self):
        lp = Loop(3)
        lp.dpv(start="0 V")
        ast = lp.to_ast()
        assert ast.steps[0].technique == "dpv"

    def test_loop_swv(self):
        lp = Loop(3)
        lp.swv(frequency="25 Hz")
        ast = lp.to_ast()
        assert ast.steps[0].technique == "swv"

    def test_loop_gcd(self):
        lp = Loop(3)
        lp.gcd(current="5 mA")
        ast = lp.to_ast()
        assert ast.steps[0].technique == "gcd"

    def test_loop_cc(self):
        lp = Loop(3)
        lp.cc(current="1 mA")
        ast = lp.to_ast()
        assert ast.steps[0].technique == "cc"

    def test_loop_stripping(self):
        lp = Loop(3)
        lp.stripping(deposition_potential="-0.5 V")
        ast = lp.to_ast()
        assert ast.steps[0].technique == "stripping"

    def test_loop_purge(self):
        lp = Loop(3)
        lp.purge(gas="N2")
        ast = lp.to_ast()
        assert ast.steps[0].technique == "purge"

    def test_loop_fluent_chaining(self):
        lp = Loop(2)
        result = lp.cv(rate="50 mV/s").ocp(duration="10 s").eis(frequency="1 kHz")
        assert result is lp
        ast = lp.to_ast()
        assert len(ast.steps) == 3

    def test_phase_loop_integration(self):
        """Loop added via Phase.loop() should appear in the AST as a LoopAST."""
        phase = Phase("test")
        lp = phase.loop(5, stop_if="degradation > 10%")
        lp.cv(rate="50 mV/s")
        ast = phase.to_ast()
        assert len(ast.steps) == 1
        assert isinstance(ast.steps[0], LoopAST)
        assert ast.steps[0].count == 5
        assert ast.steps[0].stop_if == "degradation > 10%"
