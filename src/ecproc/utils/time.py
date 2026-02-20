"""Duration parsing utilities."""

from __future__ import annotations

import re

_DURATION_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(s|ms|min|h|hr|hrs|sec|secs|seconds|minutes|hours)\s*$",
    re.IGNORECASE,
)

_UNIT_TO_SECONDS: dict[str, float] = {
    "s": 1.0,
    "sec": 1.0,
    "secs": 1.0,
    "seconds": 1.0,
    "ms": 1e-3,
    "min": 60.0,
    "minutes": 60.0,
    "h": 3600.0,
    "hr": 3600.0,
    "hrs": 3600.0,
    "hours": 3600.0,
}


def parse_duration(text: str) -> float:
    """Parse a duration string to seconds.

    Supports: s, ms, min, h (and common variants).

    Args:
        text: Duration string like '20 min', '2 h', '500 ms'.

    Returns:
        Duration in seconds.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    m = _DURATION_RE.match(text)
    if not m:
        raise ValueError(f"Cannot parse duration from: {text!r}")
    value = float(m.group(1))
    unit = m.group(2).lower()
    if unit not in _UNIT_TO_SECONDS:
        raise ValueError(f"Unknown duration unit: {unit!r}")
    return value * _UNIT_TO_SECONDS[unit]
