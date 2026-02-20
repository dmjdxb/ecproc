"""Tests for ecproc.utils.time — duration parsing."""

from __future__ import annotations

import pytest

from ecproc.utils.time import parse_duration

# ---------------------------------------------------------------------------
# Explicit named tests
# ---------------------------------------------------------------------------


class TestParseDuration:
    """Tests for parse_duration()."""

    def test_minutes(self):
        assert parse_duration("20 min") == pytest.approx(1200.0)

    def test_hours(self):
        assert parse_duration("2 h") == pytest.approx(7200.0)

    def test_milliseconds(self):
        assert parse_duration("500 ms") == pytest.approx(0.5)

    def test_seconds(self):
        assert parse_duration("30 s") == pytest.approx(30.0)

    def test_hours_long_form(self):
        assert parse_duration("1.5 hours") == pytest.approx(5400.0)

    def test_fractional_minutes(self):
        assert parse_duration("0.5 min") == pytest.approx(30.0)

    def test_case_insensitive(self):
        assert parse_duration("20 MIN") == pytest.approx(1200.0)

    def test_no_space(self):
        assert parse_duration("30s") == pytest.approx(30.0)

    def test_whitespace_padding(self):
        assert parse_duration("  2 h  ") == pytest.approx(7200.0)

    def test_error_on_invalid_input(self):
        with pytest.raises(ValueError, match="Cannot parse duration"):
            parse_duration("not a duration")

    def test_error_on_empty_string(self):
        with pytest.raises(ValueError, match="Cannot parse duration"):
            parse_duration("")

    def test_error_on_number_only(self):
        with pytest.raises(ValueError, match="Cannot parse duration"):
            parse_duration("42")


# ---------------------------------------------------------------------------
# Parametrized over all supported unit variants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected_seconds",
    [
        ("1 s", 1.0),
        ("1 sec", 1.0),
        ("1 secs", 1.0),
        ("1 seconds", 1.0),
        ("1 ms", 1e-3),
        ("1 min", 60.0),
        ("1 minutes", 60.0),
        ("1 h", 3600.0),
        ("1 hr", 3600.0),
        ("1 hrs", 3600.0),
        ("1 hours", 3600.0),
    ],
)
def test_all_supported_units(text: str, expected_seconds: float):
    """Every recognized unit variant should parse correctly with value 1."""
    assert parse_duration(text) == pytest.approx(expected_seconds)
