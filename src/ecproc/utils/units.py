"""Unit parsing and conversion for electrochemistry values.

IR canonical units (SI base):
    Potential = V, Current = A, Duration = s, Frequency = Hz,
    Temperature = C (exception to SI), Scan rate = V/s,
    Area = m^2, Loading = kg/m^2, Concentration = mol/m^3

YAML input / display output uses human-friendly units:
    mV/s, mA, cm^2, ug/cm^2, M, kHz, etc.

Conversion happens at the AST -> IR boundary (normalize in ir/generator.py)
and IR -> display boundary (format in CLI/targets).
"""

from __future__ import annotations

import re

# Maps user-facing unit strings to (SI unit, multiplier)
_UNIT_CONVERSIONS: dict[str, tuple[str, float]] = {
    # Potential
    "V": ("V", 1.0),
    "mV": ("V", 1e-3),
    "uV": ("V", 1e-6),
    # Current
    "A": ("A", 1.0),
    "mA": ("A", 1e-3),
    "uA": ("A", 1e-6),
    "nA": ("A", 1e-9),
    # Scan rate
    "V/s": ("V/s", 1.0),
    "mV/s": ("V/s", 1e-3),
    # Frequency
    "Hz": ("Hz", 1.0),
    "kHz": ("Hz", 1e3),
    "MHz": ("Hz", 1e6),
    "mHz": ("Hz", 1e-3),
    "uHz": ("Hz", 1e-6),
    # Duration
    "s": ("s", 1.0),
    "ms": ("s", 1e-3),
    "min": ("s", 60.0),
    "h": ("s", 3600.0),
    # Area
    "m2": ("m2", 1.0),
    "cm2": ("m2", 1e-4),
    "mm2": ("m2", 1e-6),
    # Loading
    "kg/m2": ("kg/m2", 1.0),
    "g/m2": ("kg/m2", 1e-3),
    "mg/cm2": ("kg/m2", 1e-2),
    "ug/cm2": ("kg/m2", 1e-5),
    # Concentration
    "mol/m3": ("mol/m3", 1.0),
    "M": ("mol/m3", 1e3),
    "mM": ("mol/m3", 1.0),
    # Temperature (stays as C)
    "C": ("C", 1.0),
    "K": ("K", 1.0),
    # Rotation
    "rpm": ("rpm", 1.0),
    # Amplitude (treated as potential)
    # Resistance
    "ohm": ("ohm", 1.0),
    "mohm": ("ohm", 1e-3),
}

_VALUE_UNIT_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z/%][a-zA-Z0-9/%·]*)\s*$"
)

_RANGE_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z]+)"
    r"\s+and\s+"
    r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z]+)\s*$"
)


def parse_value_unit(text: str) -> tuple[float, str]:
    """Parse a value+unit string like '50 mV/s' -> (50.0, 'mV/s').

    Args:
        text: String with numeric value and unit.

    Returns:
        Tuple of (value, unit_string).

    Raises:
        ValueError: If the string cannot be parsed.
    """
    m = _VALUE_UNIT_RE.match(text)
    if not m:
        raise ValueError(f"Cannot parse value+unit from: {text!r}")
    return float(m.group(1)), m.group(2)


def parse_range(text: str) -> tuple[float, float, str]:
    """Parse a range string like '0.05 V and 1.2 V' -> (0.05, 1.2, 'V').

    Args:
        text: Range string with two values and units.

    Returns:
        Tuple of (low, high, unit).

    Raises:
        ValueError: If the string cannot be parsed or units differ.
    """
    m = _RANGE_RE.match(text)
    if not m:
        raise ValueError(f"Cannot parse range from: {text!r}")
    v1, u1, v2, u2 = float(m.group(1)), m.group(2), float(m.group(3)), m.group(4)
    if u1 != u2:
        raise ValueError(f"Range units must match: {u1!r} != {u2!r}")
    return v1, v2, u1


def normalize_to_si(value: float, unit: str) -> tuple[float, str]:
    """Convert a value from user-facing unit to SI base unit.

    Args:
        value: Numeric value.
        unit: User-facing unit string (e.g., 'mV/s').

    Returns:
        Tuple of (si_value, si_unit).

    Raises:
        ValueError: If the unit is not recognized.
    """
    if unit not in _UNIT_CONVERSIONS:
        raise ValueError(f"Unknown unit: {unit!r}")
    si_unit, multiplier = _UNIT_CONVERSIONS[unit]
    return value * multiplier, si_unit


def si_to_display(value: float, si_unit: str, display_unit: str) -> float:
    """Convert SI value back to display unit for output.

    Args:
        value: SI value.
        si_unit: SI unit string.
        display_unit: Desired display unit.

    Returns:
        Value in display units.
    """
    if display_unit not in _UNIT_CONVERSIONS:
        raise ValueError(f"Unknown display unit: {display_unit!r}")
    target_si, multiplier = _UNIT_CONVERSIONS[display_unit]
    if target_si != si_unit:
        raise ValueError(f"Cannot convert {si_unit} to {display_unit}")
    return value / multiplier
