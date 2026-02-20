"""Tests for ecproc.utils.units — unit parsing and conversion."""

from __future__ import annotations

import pytest

from ecproc.utils.units import (
    normalize_to_si,
    parse_range,
    parse_value_unit,
    si_to_display,
)

# ---------------------------------------------------------------------------
# parse_value_unit
# ---------------------------------------------------------------------------


class TestParseValueUnit:
    """Tests for parse_value_unit()."""

    def test_scan_rate(self):
        value, unit = parse_value_unit("50 mV/s")
        assert value == 50.0
        assert unit == "mV/s"

    def test_voltage(self):
        value, unit = parse_value_unit("1.2 V")
        assert value == 1.2
        assert unit == "V"

    def test_frequency(self):
        value, unit = parse_value_unit("100 kHz")
        assert value == 100.0
        assert unit == "kHz"

    def test_current(self):
        value, unit = parse_value_unit("0.1 A")
        assert value == pytest.approx(0.1)
        assert unit == "A"

    def test_area(self):
        value, unit = parse_value_unit("20 cm2")
        assert value == 20.0
        assert unit == "cm2"

    def test_negative_value(self):
        value, unit = parse_value_unit("-0.5 V")
        assert value == -0.5
        assert unit == "V"

    def test_scientific_notation(self):
        value, unit = parse_value_unit("1.5e-3 A")
        assert value == pytest.approx(1.5e-3)
        assert unit == "A"

    def test_no_space(self):
        value, unit = parse_value_unit("50mV/s")
        assert value == 50.0
        assert unit == "mV/s"

    def test_whitespace_around(self):
        value, unit = parse_value_unit("  10 V  ")
        assert value == 10.0
        assert unit == "V"

    def test_error_on_empty_string(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_value_unit("")

    def test_error_on_no_unit(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_value_unit("50")

    def test_error_on_no_number(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_value_unit("mV/s")

    def test_error_on_nonsense(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_value_unit("hello world")


# ---------------------------------------------------------------------------
# parse_range
# ---------------------------------------------------------------------------


class TestParseRange:
    """Tests for parse_range()."""

    def test_voltage_range(self):
        low, high, unit = parse_range("0.05 V and 1.2 V")
        assert low == pytest.approx(0.05)
        assert high == pytest.approx(1.2)
        assert unit == "V"

    def test_current_range(self):
        low, high, unit = parse_range("0 mA and 100 mA")
        assert low == 0.0
        assert high == 100.0
        assert unit == "mA"

    def test_negative_range(self):
        low, high, unit = parse_range("-0.5 V and 2.0 V")
        assert low == pytest.approx(-0.5)
        assert high == pytest.approx(2.0)
        assert unit == "V"

    def test_error_on_mismatched_units(self):
        with pytest.raises(ValueError, match="must match"):
            parse_range("0.05 V and 100 mA")

    def test_error_on_invalid_format(self):
        with pytest.raises(ValueError, match="Cannot parse range"):
            parse_range("0.05 V to 1.2 V")

    def test_error_on_empty(self):
        with pytest.raises(ValueError, match="Cannot parse range"):
            parse_range("")


# ---------------------------------------------------------------------------
# normalize_to_si
# ---------------------------------------------------------------------------


class TestNormalizeToSI:
    """Tests for normalize_to_si()."""

    def test_mV_per_s_to_V_per_s(self):
        value, unit = normalize_to_si(50.0, "mV/s")
        assert value == pytest.approx(0.05)
        assert unit == "V/s"

    def test_mA_to_A(self):
        value, unit = normalize_to_si(100.0, "mA")
        assert value == pytest.approx(0.1)
        assert unit == "A"

    def test_cm2_to_m2(self):
        value, unit = normalize_to_si(20.0, "cm2")
        assert value == pytest.approx(20.0 * 1e-4)
        assert unit == "m2"

    def test_M_to_mol_per_m3(self):
        value, unit = normalize_to_si(0.5, "M")
        assert value == pytest.approx(500.0)
        assert unit == "mol/m3"

    def test_kHz_to_Hz(self):
        value, unit = normalize_to_si(100.0, "kHz")
        assert value == pytest.approx(100_000.0)
        assert unit == "Hz"

    def test_ug_per_cm2_to_kg_per_m2(self):
        value, unit = normalize_to_si(200.0, "ug/cm2")
        assert value == pytest.approx(200.0 * 1e-5)
        assert unit == "kg/m2"

    def test_V_identity(self):
        value, unit = normalize_to_si(1.0, "V")
        assert value == pytest.approx(1.0)
        assert unit == "V"

    def test_A_identity(self):
        value, unit = normalize_to_si(1.0, "A")
        assert value == pytest.approx(1.0)
        assert unit == "A"

    def test_error_on_unknown_unit(self):
        with pytest.raises(ValueError, match="Unknown unit"):
            normalize_to_si(1.0, "furlongs")


# ---------------------------------------------------------------------------
# si_to_display
# ---------------------------------------------------------------------------


class TestSIToDisplay:
    """Tests for si_to_display()."""

    def test_V_per_s_to_mV_per_s(self):
        result = si_to_display(0.05, "V/s", "mV/s")
        assert result == pytest.approx(50.0)

    def test_A_to_mA(self):
        result = si_to_display(0.1, "A", "mA")
        assert result == pytest.approx(100.0)

    def test_m2_to_cm2(self):
        result = si_to_display(20.0 * 1e-4, "m2", "cm2")
        assert result == pytest.approx(20.0)

    def test_mol_per_m3_to_M(self):
        result = si_to_display(500.0, "mol/m3", "M")
        assert result == pytest.approx(0.5)

    def test_Hz_to_kHz(self):
        result = si_to_display(100_000.0, "Hz", "kHz")
        assert result == pytest.approx(100.0)

    def test_kg_per_m2_to_ug_per_cm2(self):
        result = si_to_display(200.0 * 1e-5, "kg/m2", "ug/cm2")
        assert result == pytest.approx(200.0)

    def test_error_on_unknown_display_unit(self):
        with pytest.raises(ValueError, match="Unknown display unit"):
            si_to_display(1.0, "V", "furlongs")

    def test_error_on_incompatible_units(self):
        with pytest.raises(ValueError, match="Cannot convert"):
            si_to_display(1.0, "V", "mA")

    def test_roundtrip_mV_per_s(self):
        """normalize then display should round-trip."""
        si_val, si_unit = normalize_to_si(50.0, "mV/s")
        display_val = si_to_display(si_val, si_unit, "mV/s")
        assert display_val == pytest.approx(50.0)

    def test_roundtrip_ug_per_cm2(self):
        si_val, si_unit = normalize_to_si(200.0, "ug/cm2")
        display_val = si_to_display(si_val, si_unit, "ug/cm2")
        assert display_val == pytest.approx(200.0)
