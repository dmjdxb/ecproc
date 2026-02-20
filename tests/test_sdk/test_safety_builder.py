"""Tests for ecproc.sdk.safety — SafetyBuilder fluent API."""

from __future__ import annotations

from ecproc.parser.ast import ReferenceMonitorAST, SafetyAST, ThermalRunawayAST
from ecproc.sdk.safety import SafetyBuilder

# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


class TestSafetyBuilderCreation:
    """Tests for SafetyBuilder instantiation."""

    def test_creates_empty_builder(self):
        builder = SafetyBuilder()
        assert builder._max_current is None
        assert builder._voltage_window is None
        assert builder._temperature_limits is None
        assert builder._stop_if is None
        assert builder._thermal_runaway is None
        assert builder._ref_monitor is None

    def test_build_empty_returns_safety_ast(self):
        ast = SafetyBuilder().build()
        assert isinstance(ast, SafetyAST)
        assert ast.max_current is None
        assert ast.voltage_window is None
        assert ast.stop_if is None


# ---------------------------------------------------------------------------
# Individual constraint methods
# ---------------------------------------------------------------------------


class TestSafetyBuilderMethods:
    """Tests for individual builder methods."""

    def test_max_current(self):
        ast = SafetyBuilder().max_current("100 mA").build()
        assert ast.max_current == "100 mA"

    def test_voltage_window(self):
        ast = SafetyBuilder().voltage_window("-0.5 V", "2.0 V").build()
        assert ast.voltage_window == ["-0.5 V", "2.0 V"]

    def test_temperature_limits(self):
        ast = SafetyBuilder().temperature_limits("10 C", "80 C").build()
        assert ast.temperature_limits == ["10 C", "80 C"]

    def test_stop_if_single_condition(self):
        ast = SafetyBuilder().stop_if("current > 200 mA").build()
        assert ast.stop_if == ["current > 200 mA"]

    def test_stop_if_multiple_conditions(self):
        ast = SafetyBuilder().stop_if("current > 200 mA", "voltage > 3 V").build()
        assert ast.stop_if == ["current > 200 mA", "voltage > 3 V"]

    def test_thermal_runaway_default_action(self):
        ast = SafetyBuilder().thermal_runaway(max_dT_dt=5.0).build()
        assert isinstance(ast.thermal_runaway, ThermalRunawayAST)
        assert ast.thermal_runaway.max_dT_dt == 5.0
        assert ast.thermal_runaway.action == "emergency_stop"

    def test_thermal_runaway_custom_action(self):
        ast = SafetyBuilder().thermal_runaway(max_dT_dt=3.0, action="cell_off").build()
        assert ast.thermal_runaway.action == "cell_off"
        assert ast.thermal_runaway.max_dT_dt == 3.0

    def test_reference_monitor_all_fields(self):
        ast = (
            SafetyBuilder()
            .reference_monitor(
                max_Ru_change="10x",
                max_ocp_drift="500 mV/s",
                action="cell_off",
            )
            .build()
        )
        ref = ast.reference_electrode_monitor
        assert isinstance(ref, ReferenceMonitorAST)
        assert ref.max_Ru_change == "10x"
        assert ref.max_ocp_drift == "500 mV/s"
        assert ref.action == "cell_off"

    def test_reference_monitor_defaults(self):
        ast = SafetyBuilder().reference_monitor(max_Ru_change="5x").build()
        ref = ast.reference_electrode_monitor
        assert ref.max_Ru_change == "5x"
        assert ref.max_ocp_drift is None
        assert ref.action == "cell_off"


# ---------------------------------------------------------------------------
# Fluent API chaining
# ---------------------------------------------------------------------------


class TestSafetyBuilderFluent:
    """Tests for fluent method chaining."""

    def test_all_methods_return_self(self):
        builder = SafetyBuilder()
        result = builder.max_current("100 mA")
        assert result is builder

        result = builder.voltage_window("-0.5 V", "2.0 V")
        assert result is builder

        result = builder.temperature_limits("10 C", "80 C")
        assert result is builder

        result = builder.stop_if("current > 200 mA")
        assert result is builder

        result = builder.thermal_runaway(max_dT_dt=5.0)
        assert result is builder

        result = builder.reference_monitor(max_Ru_change="10x")
        assert result is builder

    def test_full_chain_builds_complete_ast(self):
        ast = (
            SafetyBuilder()
            .max_current("100 mA")
            .voltage_window("-0.5 V", "2.0 V")
            .temperature_limits("10 C", "80 C")
            .stop_if("current > 200 mA", "temperature > 85 C")
            .thermal_runaway(max_dT_dt=5.0, action="emergency_stop")
            .reference_monitor(max_Ru_change="10x", max_ocp_drift="500 mV/s")
            .build()
        )

        assert isinstance(ast, SafetyAST)
        assert ast.max_current == "100 mA"
        assert ast.voltage_window == ["-0.5 V", "2.0 V"]
        assert ast.temperature_limits == ["10 C", "80 C"]
        assert ast.stop_if == ["current > 200 mA", "temperature > 85 C"]
        assert ast.thermal_runaway.max_dT_dt == 5.0
        assert ast.thermal_runaway.action == "emergency_stop"
        assert ast.reference_electrode_monitor.max_Ru_change == "10x"
        assert ast.reference_electrode_monitor.max_ocp_drift == "500 mV/s"

    def test_overwrite_by_calling_twice(self):
        ast = (
            SafetyBuilder()
            .max_current("50 mA")
            .max_current("100 mA")
            .build()
        )
        assert ast.max_current == "100 mA"
