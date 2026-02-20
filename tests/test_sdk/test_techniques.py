"""Tests for ecproc.sdk.techniques - all electrochemical technique classes."""

from __future__ import annotations

import pytest

from ecproc.parser.ast import StepAST
from ecproc.sdk.techniques.base import BaseTechnique
from ecproc.sdk.techniques.ca import Hold, hold
from ecproc.sdk.techniques.cc import CC, cc
from ecproc.sdk.techniques.cp import Galvanostatic, galvanostatic
from ecproc.sdk.techniques.cv import CV, cv
from ecproc.sdk.techniques.dpv import DPV, dpv
from ecproc.sdk.techniques.eis import EIS, eis
from ecproc.sdk.techniques.gcd import GCD, gcd
from ecproc.sdk.techniques.lsv import LSV, lsv
from ecproc.sdk.techniques.ocp import OCP, ocp
from ecproc.sdk.techniques.stripping import Stripping, stripping
from ecproc.sdk.techniques.swv import SWV, swv

# ---------------------------------------------------------------------------
# CV (Cyclic Voltammetry)
# ---------------------------------------------------------------------------


class TestCV:
    """Test CV technique construction and validation."""

    def test_cv_basic_params(self):
        t = CV(0.05, 1.2, rate=50, cycles=10)
        assert t.vertex1 == 0.05
        assert t.vertex2 == 1.2
        assert t.rate == 50
        assert t.cycles == 10

    def test_cv_default_params(self):
        t = CV(0.0, 1.0)
        assert t.rate == 50.0
        assert t.cycles == 1
        assert t.start == "negative"

    def test_cv_to_step_ast(self):
        t = CV(0.05, 1.2, rate=100, cycles=5)
        step = t.to_step_ast()
        assert isinstance(step, StepAST)
        assert step.technique == "cv"
        assert step.parameters["vertex1"] == 0.05
        assert step.parameters["vertex2"] == 1.2
        assert step.parameters["rate"] == 100
        assert step.parameters["cycles"] == 5

    def test_cv_validate_negative_rate(self):
        t = CV(0.05, 1.2, rate=-10, cycles=5)
        errors = t.validate_params()
        assert any("rate" in e.lower() or "positive" in e.lower() for e in errors)

    def test_cv_validate_zero_cycles(self):
        t = CV(0.05, 1.2, rate=50, cycles=0)
        errors = t.validate_params()
        assert any("cycle" in e.lower() for e in errors)

    def test_cv_validate_equal_vertices(self):
        t = CV(1.0, 1.0, rate=50, cycles=1)
        errors = t.validate_params()
        assert any("vertex" in e.lower() or "differ" in e.lower() for e in errors)

    def test_cv_valid_returns_no_errors(self):
        t = CV(0.05, 1.2, rate=50, cycles=10)
        assert t.validate_params() == []

    def test_cv_convenience_constructor(self):
        t = cv(0.05, 1.2, rate=100, cycles=5)
        assert isinstance(t, CV)
        assert t.rate == 100


# ---------------------------------------------------------------------------
# EIS (Electrochemical Impedance Spectroscopy)
# ---------------------------------------------------------------------------


class TestEIS:
    """Test EIS technique construction and validation."""

    def test_eis_basic_params(self):
        t = EIS(100000, 0.1, amplitude=10, ppd=10)
        assert t.f_start == 100000
        assert t.f_end == 0.1
        assert t.amplitude == 10
        assert t.ppd == 10

    def test_eis_default_at_ocp(self):
        t = EIS(100000, 0.1)
        assert t.at == "OCP"
        assert t.amplitude == 10.0

    def test_eis_to_step_ast(self):
        t = EIS(100000, 0.1, amplitude=5, at=0.5, ppd=20)
        step = t.to_step_ast()
        assert step.technique == "eis"
        assert step.parameters["f_start"] == 100000
        assert step.parameters["f_end"] == 0.1
        assert step.parameters["amplitude"] == 5
        assert step.parameters["at"] == 0.5
        assert step.parameters["ppd"] == 20

    def test_eis_validate_negative_frequency(self):
        t = EIS(-100, 0.1)
        errors = t.validate_params()
        assert len(errors) > 0

    def test_eis_validate_negative_amplitude(self):
        t = EIS(100000, 0.1, amplitude=-5)
        errors = t.validate_params()
        assert any("amplitude" in e.lower() for e in errors)

    def test_eis_validate_zero_ppd(self):
        t = EIS(100000, 0.1, ppd=0)
        errors = t.validate_params()
        assert any("points" in e.lower() or "ppd" in e.lower() for e in errors)

    def test_eis_convenience_constructor(self):
        t = eis(100000, 0.1, amplitude=5)
        assert isinstance(t, EIS)
        assert t.amplitude == 5


# ---------------------------------------------------------------------------
# LSV (Linear Sweep Voltammetry)
# ---------------------------------------------------------------------------


class TestLSV:
    """Test LSV technique construction and validation."""

    def test_lsv_basic_params(self):
        t = LSV(0.0, 1.0, rate=10)
        assert t.start == 0.0
        assert t.end == 1.0
        assert t.rate == 10

    def test_lsv_to_step_ast(self):
        t = LSV(0.0, 1.0, rate=10)
        step = t.to_step_ast()
        assert step.technique == "lsv"
        assert step.parameters["start"] == 0.0
        assert step.parameters["end"] == 1.0
        assert step.parameters["rate"] == 10

    def test_lsv_validate_negative_rate(self):
        t = LSV(0.0, 1.0, rate=-5)
        errors = t.validate_params()
        assert len(errors) > 0

    def test_lsv_validate_equal_start_end(self):
        t = LSV(0.5, 0.5)
        errors = t.validate_params()
        assert any("start" in e.lower() or "differ" in e.lower() for e in errors)

    def test_lsv_convenience_constructor(self):
        t = lsv(0.0, 1.0, rate=20)
        assert isinstance(t, LSV)


# ---------------------------------------------------------------------------
# OCP (Open Circuit Potential)
# ---------------------------------------------------------------------------


class TestOCP:
    """Test OCP technique construction and validation."""

    def test_ocp_with_stable_and_timeout(self):
        t = OCP(stable="1 mV/s", timeout="5 min")
        assert t.stable == "1 mV/s"
        assert t.timeout == "5 min"

    def test_ocp_defaults_to_none(self):
        t = OCP()
        assert t.stable is None
        assert t.timeout is None

    def test_ocp_to_step_ast(self):
        t = OCP(stable="1 mV/s", timeout="5 min")
        step = t.to_step_ast()
        assert step.technique == "ocp"
        assert step.parameters["stable"] == "1 mV/s"
        assert step.parameters["timeout"] == "5 min"

    def test_ocp_to_step_ast_no_params(self):
        t = OCP()
        step = t.to_step_ast()
        assert step.technique == "ocp"
        assert step.parameters == {}

    def test_ocp_validate_always_passes(self):
        t = OCP()
        assert t.validate_params() == []

    def test_ocp_convenience_constructor(self):
        t = ocp(stable="0.5 mV/s")
        assert isinstance(t, OCP)
        assert t.stable == "0.5 mV/s"


# ---------------------------------------------------------------------------
# Hold / CA (Chronoamperometry)
# ---------------------------------------------------------------------------


class TestHold:
    """Test Hold (CA) technique construction and validation."""

    def test_hold_basic_params(self):
        t = Hold(0.5, "30 min")
        assert t.potential == 0.5
        assert t.duration == "30 min"

    def test_hold_with_sample(self):
        t = Hold(1.0, "1 h", sample="1 s")
        assert t.sample == "1 s"

    def test_hold_to_step_ast(self):
        t = Hold(0.5, "30 min")
        step = t.to_step_ast()
        assert step.technique == "hold"
        assert step.parameters["potential"] == 0.5
        assert step.parameters["duration"] == "30 min"

    def test_hold_validate_empty_duration(self):
        t = Hold(0.5, "")
        errors = t.validate_params()
        assert any("duration" in e.lower() for e in errors)

    def test_hold_convenience_constructor(self):
        t = hold(0.5, "30 min")
        assert isinstance(t, Hold)


# ---------------------------------------------------------------------------
# Galvanostatic / CP (Chronopotentiometry)
# ---------------------------------------------------------------------------


class TestGalvanostatic:
    """Test Galvanostatic (CP) technique construction and validation."""

    def test_galvanostatic_basic_params(self):
        t = Galvanostatic(0.01, "1 h")
        assert t.current == 0.01
        assert t.duration == "1 h"

    def test_galvanostatic_with_cutoff(self):
        t = Galvanostatic(0.01, "1 h", cutoff=2.0)
        assert t.cutoff == 2.0

    def test_galvanostatic_to_step_ast(self):
        t = Galvanostatic(0.01, "2 h", sample="5 s")
        step = t.to_step_ast()
        assert step.technique == "galvanostatic"
        assert step.parameters["current"] == 0.01
        assert step.parameters["duration"] == "2 h"
        assert step.parameters["sample"] == "5 s"

    def test_galvanostatic_validate_empty_duration(self):
        t = Galvanostatic(0.01, "")
        errors = t.validate_params()
        assert len(errors) > 0

    def test_galvanostatic_convenience_constructor(self):
        t = galvanostatic(0.01, "1 h")
        assert isinstance(t, Galvanostatic)


# ---------------------------------------------------------------------------
# DPV (Differential Pulse Voltammetry)
# ---------------------------------------------------------------------------


class TestDPV:
    """Test DPV technique construction and validation."""

    def test_dpv_basic_params(self):
        t = DPV(-0.5, 0.5, step=5.0, pulse_height=50.0, pulse_width=50.0)
        assert t.start == -0.5
        assert t.end == 0.5
        assert t.step == 5.0
        assert t.pulse_height == 50.0
        assert t.pulse_width == 50.0

    def test_dpv_to_step_ast(self):
        t = DPV(-0.5, 0.5)
        step = t.to_step_ast()
        assert step.technique == "dpv"
        assert step.parameters["start"] == -0.5
        assert step.parameters["end"] == 0.5

    def test_dpv_validate_equal_start_end(self):
        t = DPV(0.5, 0.5)
        errors = t.validate_params()
        assert any("start" in e.lower() or "differ" in e.lower() for e in errors)

    def test_dpv_validate_negative_step(self):
        t = DPV(-0.5, 0.5, step=-1)
        errors = t.validate_params()
        assert any("step" in e.lower() for e in errors)

    def test_dpv_convenience_constructor(self):
        t = dpv(-0.5, 0.5, pulse_height=25)
        assert isinstance(t, DPV)
        assert t.pulse_height == 25


# ---------------------------------------------------------------------------
# SWV (Square Wave Voltammetry)
# ---------------------------------------------------------------------------


class TestSWV:
    """Test SWV technique construction and validation."""

    def test_swv_basic_params(self):
        t = SWV(-0.5, 0.5, frequency=25, amplitude=25, step=4)
        assert t.start == -0.5
        assert t.end == 0.5
        assert t.frequency == 25
        assert t.amplitude == 25
        assert t.step == 4

    def test_swv_to_step_ast(self):
        t = SWV(-0.5, 0.5)
        step = t.to_step_ast()
        assert step.technique == "swv"
        assert step.parameters["frequency"] == 25.0

    def test_swv_validate_zero_frequency(self):
        t = SWV(-0.5, 0.5, frequency=0)
        errors = t.validate_params()
        assert any("frequency" in e.lower() for e in errors)

    def test_swv_validate_negative_amplitude(self):
        t = SWV(-0.5, 0.5, amplitude=-10)
        errors = t.validate_params()
        assert any("amplitude" in e.lower() for e in errors)

    def test_swv_convenience_constructor(self):
        t = swv(-0.5, 0.5, frequency=50)
        assert isinstance(t, SWV)
        assert t.frequency == 50


# ---------------------------------------------------------------------------
# GCD (Galvanostatic Charge-Discharge)
# ---------------------------------------------------------------------------


class TestGCD:
    """Test GCD technique construction and validation."""

    def test_gcd_basic_params(self):
        t = GCD(0.001, voltage_limits=[0.0, 1.5], cycles=100)
        assert t.current == 0.001
        assert t.voltage_limits == [0.0, 1.5]
        assert t.cycles == 100

    def test_gcd_to_step_ast(self):
        t = GCD(0.001, voltage_limits=[0.0, 1.5], cycles=10)
        step = t.to_step_ast()
        assert step.technique == "gcd"
        assert step.parameters["current"] == 0.001
        assert step.parameters["cycles"] == 10
        assert step.parameters["voltage_limits"] == [0.0, 1.5]

    def test_gcd_validate_zero_current(self):
        t = GCD(0.0, cycles=10)
        errors = t.validate_params()
        assert any("current" in e.lower() for e in errors)

    def test_gcd_validate_zero_cycles(self):
        t = GCD(0.001, cycles=0)
        errors = t.validate_params()
        assert any("cycle" in e.lower() for e in errors)

    def test_gcd_validate_bad_voltage_limits(self):
        t = GCD(0.001, voltage_limits=[0.0, 1.0, 2.0])
        errors = t.validate_params()
        assert any("voltage" in e.lower() or "pair" in e.lower() for e in errors)

    def test_gcd_convenience_constructor(self):
        t = gcd(0.001, cycles=50)
        assert isinstance(t, GCD)


# ---------------------------------------------------------------------------
# CC (Constant Current / Coulometry)
# ---------------------------------------------------------------------------


class TestCC:
    """Test CC technique construction and validation."""

    def test_cc_basic_params(self):
        t = CC(1.0, "10 min")
        assert t.potential == 1.0
        assert t.duration == "10 min"

    def test_cc_to_step_ast(self):
        t = CC(1.0, "10 min", sample="1 s")
        step = t.to_step_ast()
        assert step.technique == "cc"
        assert step.parameters["potential"] == 1.0
        assert step.parameters["duration"] == "10 min"
        assert step.parameters["sample"] == "1 s"

    def test_cc_validate_empty_duration(self):
        t = CC(1.0, "")
        errors = t.validate_params()
        assert any("duration" in e.lower() for e in errors)

    def test_cc_convenience_constructor(self):
        t = cc(1.0, "10 min")
        assert isinstance(t, CC)


# ---------------------------------------------------------------------------
# Stripping
# ---------------------------------------------------------------------------


class TestStripping:
    """Test Stripping technique construction and validation."""

    def test_stripping_basic_params(self):
        t = Stripping(-1.2, "120 s", -1.2, 0.2, rate=50)
        assert t.deposition_potential == -1.2
        assert t.deposition_time == "120 s"
        assert t.scan_start == -1.2
        assert t.scan_end == 0.2
        assert t.rate == 50

    def test_stripping_to_step_ast(self):
        t = Stripping(-1.2, "120 s", -1.2, 0.2)
        step = t.to_step_ast()
        assert step.technique == "stripping"
        assert step.parameters["deposition_potential"] == -1.2
        assert step.parameters["deposition_time"] == "120 s"
        assert step.parameters["scan_start"] == -1.2
        assert step.parameters["scan_end"] == 0.2

    def test_stripping_validate_empty_deposition_time(self):
        t = Stripping(-1.2, "", -1.2, 0.2)
        errors = t.validate_params()
        assert any("deposition" in e.lower() for e in errors)

    def test_stripping_validate_equal_scan_range(self):
        t = Stripping(-1.2, "120 s", 0.5, 0.5)
        errors = t.validate_params()
        assert any("scan" in e.lower() or "differ" in e.lower() for e in errors)

    def test_stripping_validate_negative_rate(self):
        t = Stripping(-1.2, "120 s", -1.2, 0.2, rate=-10)
        errors = t.validate_params()
        assert any("rate" in e.lower() for e in errors)

    def test_stripping_convenience_constructor(self):
        t = stripping(-1.2, "120 s", -1.2, 0.2, rate=100)
        assert isinstance(t, Stripping)
        assert t.rate == 100


# ---------------------------------------------------------------------------
# Tag, Extract, and Vendor Flags (cross-technique)
# ---------------------------------------------------------------------------


class TestTechniqueMetadata:
    """Test tag, extract, and vendor_flags on technique objects."""

    def test_technique_with_tag(self):
        t = CV(0.05, 1.2, tag="bol_cv")
        assert t.tag == "bol_cv"
        step = t.to_step_ast()
        assert step.tag == "bol_cv"

    def test_technique_with_extract_string(self):
        t = EIS(100000, 0.1, tag="eis_check", extract="Ru")
        assert t.extract == "Ru"
        step = t.to_step_ast()
        assert step.extract == "Ru"

    def test_technique_with_extract_dict(self):
        t = EIS(100000, 0.1, extract={"Ru": "R_uncompensated", "Cdl": "C_double_layer"})
        step = t.to_step_ast()
        assert step.extract == {"Ru": "R_uncompensated", "Cdl": "C_double_layer"}

    def test_technique_with_vendor_flags(self):
        flags = {"biologic": {"bandwidth": 5}, "autolab": {"FRA_mode": "single"}}
        t = CV(0.05, 1.2, vendor_flags=flags)
        assert t.vendor_flags == flags
        step = t.to_step_ast()
        assert step.vendor_flags == flags

    def test_technique_without_metadata(self):
        t = CV(0.05, 1.2)
        assert t.tag is None
        assert t.extract is None
        assert t.vendor_flags is None
        step = t.to_step_ast()
        assert step.tag is None
        assert step.extract is None
        assert step.vendor_flags is None


# ---------------------------------------------------------------------------
# Base class checks
# ---------------------------------------------------------------------------


class TestBaseTechnique:
    """Test that BaseTechnique is properly abstract."""

    def test_cannot_instantiate_base(self):
        with pytest.raises(TypeError):
            BaseTechnique()

    def test_all_techniques_are_subclasses(self):
        for cls in [CV, EIS, LSV, OCP, Hold, Galvanostatic, DPV, SWV, GCD, CC, Stripping]:
            assert issubclass(cls, BaseTechnique)

    @pytest.mark.parametrize(
        "cls,technique_name",
        [
            (CV, "cv"),
            (EIS, "eis"),
            (LSV, "lsv"),
            (OCP, "ocp"),
            (Hold, "hold"),
            (Galvanostatic, "galvanostatic"),
            (DPV, "dpv"),
            (SWV, "swv"),
            (GCD, "gcd"),
            (CC, "cc"),
            (Stripping, "stripping"),
        ],
    )
    def test_technique_name_attribute(self, cls, technique_name):
        assert cls.technique_name == technique_name
