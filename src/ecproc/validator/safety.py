"""L3: Safety validation - equipment and personnel protection checks.

Validates that the IR does not specify conditions that could damage
equipment or pose safety risks.
"""

from __future__ import annotations

from typing import Any

from ecproc.ir.schema import FaradayIR, IRLoop, IRPhase, IRStep
from ecproc.validator.errors import ValidationResult


def validate_safety(ir: FaradayIR) -> ValidationResult:
    """Run L3 safety validation on a FaradayIR."""
    result = ValidationResult()

    safety = ir.safety

    # If no safety block exists, warn for non-trivial procedures
    if safety is None:
        total_steps = _count_steps(ir)
        if total_steps > 5:
            result.add_warning(
                "L3", "SF001",
                f"No safety block defined for procedure with {total_steps} steps; "
                "consider adding voltage_window, max_current, or stop_conditions",
                path="safety",
            )
        return result

    # SF002: Validate voltage_window bounds
    if safety.voltage_window_V is not None:
        v_low, v_high = safety.voltage_window_V
        if v_low >= v_high:
            result.add_error(
                "L3", "SF002",
                f"Safety voltage_window lower bound ({v_low} V) must be less "
                f"than upper bound ({v_high} V)",
                path="safety.voltage_window_V",
                expected="v_low < v_high",
                actual=f"{v_low} >= {v_high}",
            )

        # Check that all step potentials fall within the voltage window
        for i, phase in enumerate(ir.procedure):
            _check_potentials_in_window(
                phase, f"procedure[{i}]", v_low, v_high, result
            )

    # SF003: Validate max_current is positive
    if safety.max_current_A is not None:
        if safety.max_current_A <= 0:
            result.add_error(
                "L3", "SF003",
                f"Safety max_current_A must be > 0, got {safety.max_current_A}",
                path="safety.max_current_A",
                expected="> 0",
                actual=safety.max_current_A,
            )

        # Check steps for current limits
        for i, phase in enumerate(ir.procedure):
            _check_current_limits(
                phase, f"procedure[{i}]", safety.max_current_A, result
            )

    # SF004: Validate temperature limits
    if safety.temperature_limits_C is not None:
        t_low, t_high = safety.temperature_limits_C
        if t_low >= t_high:
            result.add_error(
                "L3", "SF004",
                f"Safety temperature_limits_C lower bound ({t_low} C) must be "
                f"less than upper bound ({t_high} C)",
                path="safety.temperature_limits_C",
                expected="t_low < t_high",
                actual=f"{t_low} >= {t_high}",
            )
        # Absolute sanity: temperature should be within -40 to 200 C
        if t_low < -40:
            result.add_warning(
                "L3", "SF005",
                f"Safety temperature lower limit {t_low} C is unusually low",
                path="safety.temperature_limits_C",
            )
        if t_high > 200:
            result.add_warning(
                "L3", "SF006",
                f"Safety temperature upper limit {t_high} C is unusually high",
                path="safety.temperature_limits_C",
            )

    # SF007: Stop conditions for long procedures
    total_steps = _count_steps(ir)
    has_stop = safety.stop_conditions and len(safety.stop_conditions) > 0
    if total_steps > 10 and not has_stop:
        result.add_warning(
            "L3", "SF007",
            f"Procedure has {total_steps} steps but no stop_conditions defined; "
            "consider adding safety stop conditions for long experiments",
            path="safety.stop_conditions",
        )

    # SF008: Thermal runaway settings
    if safety.thermal_runaway is not None:
        tr = safety.thermal_runaway
        if tr.max_dT_dt_K_s <= 0:
            result.add_error(
                "L3", "SF008",
                f"Thermal runaway max_dT_dt_K_s must be > 0, got {tr.max_dT_dt_K_s}",
                path="safety.thermal_runaway.max_dT_dt_K_s",
            )
        if tr.action not in ("cell_off", "pause", "abort"):
            result.add_warning(
                "L3", "SF009",
                f"Thermal runaway action '{tr.action}' is non-standard; "
                "expected 'cell_off', 'pause', or 'abort'",
                path="safety.thermal_runaway.action",
            )

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_steps(ir: FaradayIR) -> int:
    """Count total number of steps across all phases."""
    total = 0
    for phase in ir.procedure:
        total += _count_steps_in_list(phase.steps)
    return total


def _count_steps_in_list(items: list[IRStep | IRLoop]) -> int:
    count = 0
    for item in items:
        if isinstance(item, IRStep):
            count += 1
        elif isinstance(item, IRLoop):
            count += _count_steps_in_list(item.steps)
    return count


def _extra(step: IRStep) -> dict[str, Any]:
    """Return extra (technique-specific) fields on an IRStep."""
    known = set(IRStep.model_fields.keys())
    return {k: v for k, v in step.model_dump().items() if k not in known}


def _check_potentials_in_window(
    phase: IRPhase,
    path: str,
    v_low: float,
    v_high: float,
    result: ValidationResult,
) -> None:
    """Check that step potentials are within the safety voltage window."""
    for j, item in enumerate(phase.steps):
        step_path = f"{path}.steps[{j}]"
        if isinstance(item, IRStep):
            extras = _extra(item)
            potential_fields = [
                "potential", "vertex1", "vertex2", "e_start", "e_end",
                "e_initial", "e_final",
            ]
            for fname in potential_fields:
                val = extras.get(fname)
                if (
                    val is not None
                    and isinstance(val, (int, float))
                    and (val < v_low or val > v_high)
                ):
                    result.add_error(
                        "L3", "SF010",
                        f"Step {fname}={val} V outside safety voltage window "
                        f"[{v_low}, {v_high}] V",
                        path=f"{step_path}.{fname}",
                        expected=f"[{v_low}, {v_high}]",
                        actual=val,
                    )
        elif isinstance(item, IRLoop):
            for k, sub in enumerate(item.steps):
                if isinstance(sub, IRStep):
                    _check_potentials_in_window_step(
                        sub, f"{step_path}.steps[{k}]", v_low, v_high, result
                    )


def _check_potentials_in_window_step(
    step: IRStep,
    path: str,
    v_low: float,
    v_high: float,
    result: ValidationResult,
) -> None:
    """Check a single step's potentials against safety voltage window."""
    extras = _extra(step)
    potential_fields = [
        "potential", "vertex1", "vertex2", "e_start", "e_end",
        "e_initial", "e_final",
    ]
    for fname in potential_fields:
        val = extras.get(fname)
        if (
            val is not None
            and isinstance(val, (int, float))
            and (val < v_low or val > v_high)
        ):
            result.add_error(
                "L3", "SF010",
                f"Step {fname}={val} V outside safety voltage window "
                f"[{v_low}, {v_high}] V",
                path=f"{path}.{fname}",
                expected=f"[{v_low}, {v_high}]",
                actual=val,
            )


def _check_current_limits(
    phase: IRPhase,
    path: str,
    max_current: float,
    result: ValidationResult,
) -> None:
    """Check that step currents do not exceed safety max_current."""
    for j, item in enumerate(phase.steps):
        step_path = f"{path}.steps[{j}]"
        if isinstance(item, IRStep):
            extras = _extra(item)
            current_fields = ["current", "i_limit", "current_limit"]
            for fname in current_fields:
                val = extras.get(fname)
                if (
                    val is not None
                    and isinstance(val, (int, float))
                    and abs(val) > max_current
                ):
                    result.add_error(
                        "L3", "SF011",
                        f"Step {fname}={val} A exceeds safety max_current "
                        f"{max_current} A",
                        path=f"{step_path}.{fname}",
                        expected=f"|I| <= {max_current}",
                        actual=val,
                    )
        elif isinstance(item, IRLoop):
            for k, sub in enumerate(item.steps):
                if isinstance(sub, IRStep):
                    _check_current_limit_step(
                        sub, f"{step_path}.steps[{k}]", max_current, result
                    )


def _check_current_limit_step(
    step: IRStep,
    path: str,
    max_current: float,
    result: ValidationResult,
) -> None:
    """Check a single step's currents against safety max_current."""
    extras = _extra(step)
    current_fields = ["current", "i_limit", "current_limit"]
    for fname in current_fields:
        val = extras.get(fname)
        if (
            val is not None
            and isinstance(val, (int, float))
            and abs(val) > max_current
        ):
            result.add_error(
                "L3", "SF011",
                f"Step {fname}={val} A exceeds safety max_current "
                f"{max_current} A",
                path=f"{path}.{fname}",
                expected=f"|I| <= {max_current}",
                actual=val,
            )
