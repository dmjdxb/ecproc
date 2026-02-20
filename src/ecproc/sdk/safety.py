"""Safety constraint builder for SDK."""

from __future__ import annotations

from ecproc.parser.ast import ReferenceMonitorAST, SafetyAST, ThermalRunawayAST


class SafetyBuilder:
    """Fluent builder for safety constraints.

    Example:
        safety = (SafetyBuilder()
            .max_current("100 mA")
            .voltage_window("-0.5 V", "2.0 V")
            .stop_if("current > 200 mA")
            .build())
    """

    def __init__(self) -> None:
        self._max_current: str | None = None
        self._voltage_window: list[str] | None = None
        self._temperature_limits: list[str] | None = None
        self._stop_if: list[str] | None = None
        self._thermal_runaway: ThermalRunawayAST | None = None
        self._ref_monitor: ReferenceMonitorAST | None = None

    def max_current(self, value: str) -> SafetyBuilder:
        """Set the maximum allowable current."""
        self._max_current = value
        return self

    def voltage_window(self, low: str, high: str) -> SafetyBuilder:
        """Set the safe voltage window [low, high]."""
        self._voltage_window = [low, high]
        return self

    def temperature_limits(self, low: str, high: str) -> SafetyBuilder:
        """Set the safe temperature range [low, high]."""
        self._temperature_limits = [low, high]
        return self

    def stop_if(self, *conditions: str) -> SafetyBuilder:
        """Add emergency stop conditions."""
        self._stop_if = list(conditions)
        return self

    def thermal_runaway(
        self, max_dT_dt: float, action: str = "emergency_stop"
    ) -> SafetyBuilder:
        """Configure thermal runaway protection.

        Args:
            max_dT_dt: Maximum allowed temperature rate of change (deg_C/min).
            action: Response action ("emergency_stop" or "cell_off").
        """
        self._thermal_runaway = ThermalRunawayAST(max_dT_dt=max_dT_dt, action=action)
        return self

    def reference_monitor(
        self,
        *,
        max_Ru_change: str | None = None,
        max_ocp_drift: str | None = None,
        action: str = "cell_off",
    ) -> SafetyBuilder:
        """Configure reference electrode health monitoring.

        Args:
            max_Ru_change: Maximum allowable uncompensated resistance change (e.g., "10x").
            max_ocp_drift: Maximum allowable OCP drift rate (e.g., "500 mV/s").
            action: Response action when limits are exceeded.
        """
        self._ref_monitor = ReferenceMonitorAST(
            max_Ru_change=max_Ru_change,
            max_ocp_drift=max_ocp_drift,
            action=action,
        )
        return self

    def build(self) -> SafetyAST:
        """Build the SafetyAST from accumulated constraints."""
        return SafetyAST(
            max_current=self._max_current,
            voltage_window=self._voltage_window,
            temperature_limits=self._temperature_limits,
            stop_if=self._stop_if,
            thermal_runaway=self._thermal_runaway,
            reference_electrode_monitor=self._ref_monitor,
        )
