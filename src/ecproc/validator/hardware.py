"""L4: Hardware validation - checks IR against a hardware profile.

Validates that the specified techniques and parameters are within
the capabilities of the target potentiostat/hardware.

Hardware profiles are plain dicts with the following structure:

    {
        "name": "Gamry Interface 1010E",
        "supported_techniques": ["cv", "eis", "lsv", "ocp", "hold", ...],
        "potential_range_V": [-12.0, 12.0],
        "current_range_A": [-1.0, 1.0],
        "frequency_range_Hz": [1e-5, 1e6],
        "max_channels": 1,
        "max_data_points": 65536,
    }
"""

from __future__ import annotations

from typing import Any

from ecproc.ir.schema import FaradayIR, IRLoop, IRPhase, IRStep
from ecproc.validator.errors import ValidationResult


def validate_hardware(
    ir: FaradayIR,
    profile: dict[str, Any],
) -> ValidationResult:
    """Run L4 hardware validation against a hardware profile dict.

    Parameters
    ----------
    ir : FaradayIR
        The intermediate representation to validate.
    profile : dict
        Hardware profile describing the potentiostat capabilities.
    """
    result = ValidationResult()

    supported = set(profile.get("supported_techniques", []))
    pot_range = profile.get("potential_range_V")
    cur_range = profile.get("current_range_A")
    freq_range = profile.get("frequency_range_Hz")

    for i, phase in enumerate(ir.procedure):
        _walk_phase(
            phase, f"procedure[{i}]", result,
            supported=supported,
            pot_range=pot_range,
            cur_range=cur_range,
            freq_range=freq_range,
        )

    return result


# ---------------------------------------------------------------------------
# Walk helpers
# ---------------------------------------------------------------------------

def _walk_phase(
    phase: IRPhase,
    path: str,
    result: ValidationResult,
    *,
    supported: set[str],
    pot_range: list[float] | tuple[float, float] | None,
    cur_range: list[float] | tuple[float, float] | None,
    freq_range: list[float] | tuple[float, float] | None,
) -> None:
    for j, item in enumerate(phase.steps):
        _walk_item(
            item, f"{path}.steps[{j}]", result,
            supported=supported,
            pot_range=pot_range,
            cur_range=cur_range,
            freq_range=freq_range,
        )


def _walk_item(
    item: IRStep | IRLoop,
    path: str,
    result: ValidationResult,
    *,
    supported: set[str],
    pot_range: list[float] | tuple[float, float] | None,
    cur_range: list[float] | tuple[float, float] | None,
    freq_range: list[float] | tuple[float, float] | None,
) -> None:
    if isinstance(item, IRStep):
        _validate_step(
            item, path, result,
            supported=supported,
            pot_range=pot_range,
            cur_range=cur_range,
            freq_range=freq_range,
        )
    elif isinstance(item, IRLoop):
        for k, sub in enumerate(item.steps):
            _walk_item(
                sub, f"{path}.steps[{k}]", result,
                supported=supported,
                pot_range=pot_range,
                cur_range=cur_range,
                freq_range=freq_range,
            )


def _extra(step: IRStep) -> dict[str, Any]:
    """Return extra (technique-specific) fields on an IRStep."""
    known = set(IRStep.model_fields.keys())
    return {k: v for k, v in step.model_dump().items() if k not in known}


def _validate_step(
    step: IRStep,
    path: str,
    result: ValidationResult,
    *,
    supported: set[str],
    pot_range: list[float] | tuple[float, float] | None,
    cur_range: list[float] | tuple[float, float] | None,
    freq_range: list[float] | tuple[float, float] | None,
) -> None:
    """Validate a single step against hardware capabilities."""

    # HW001: Technique support
    if supported and step.technique not in supported:
        result.add_error(
            "L4", "HW001",
            f"Technique '{step.technique}' not supported by hardware",
            path=f"{path}.technique",
        )

    extras = _extra(step)

    # HW002: Potential range
    if pot_range is not None:
        p_lo, p_hi = pot_range[0], pot_range[1]
        potential_fields = [
            "potential", "vertex1", "vertex2", "e_start", "e_end",
            "e_initial", "e_final", "e_dc",
        ]
        for fname in potential_fields:
            val = extras.get(fname)
            if val is not None and isinstance(val, (int, float)) and (val < p_lo or val > p_hi):
                result.add_error(
                    "L4", "HW002",
                    f"Potential {fname}={val} V outside hardware range "
                    f"[{p_lo}, {p_hi}] V",
                    path=f"{path}.{fname}",
                    expected=f"[{p_lo}, {p_hi}]",
                    actual=val,
                )

    # HW003: Current range
    if cur_range is not None:
        c_lo, c_hi = cur_range[0], cur_range[1]
        current_fields = ["current", "i_limit", "current_limit"]
        for fname in current_fields:
            val = extras.get(fname)
            if val is not None and isinstance(val, (int, float)) and (val < c_lo or val > c_hi):
                result.add_error(
                    "L4", "HW003",
                    f"Current {fname}={val} A outside hardware range "
                    f"[{c_lo}, {c_hi}] A",
                    path=f"{path}.{fname}",
                    expected=f"[{c_lo}, {c_hi}]",
                    actual=val,
                )

    # HW004: Frequency range (EIS)
    if freq_range is not None and step.technique == "eis":
        f_lo, f_hi = freq_range[0], freq_range[1]
        for fname in ("f_start", "f_end"):
            val = extras.get(fname)
            if val is not None and isinstance(val, (int, float)) and (val < f_lo or val > f_hi):
                result.add_error(
                    "L4", "HW004",
                    f"Frequency {fname}={val} Hz outside hardware range "
                    f"[{f_lo}, {f_hi}] Hz",
                    path=f"{path}.{fname}",
                    expected=f"[{f_lo}, {f_hi}]",
                    actual=val,
                )
