"""Tests for ecproc.targets.python.hardware.mock - mock potentiostat."""

from __future__ import annotations

from ecproc.targets.python.hardware.base import HardwareInterface
from ecproc.targets.python.hardware.mock import MockHardware

# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


class TestMockHardwareCreation:
    """Test MockHardware instantiation."""

    def test_is_hardware_interface(self):
        hw = MockHardware()
        assert isinstance(hw, HardwareInterface)

    def test_name_is_mock(self):
        hw = MockHardware()
        assert hw.name == "mock"

    def test_initial_state(self):
        hw = MockHardware()
        assert hw._connected is False
        assert hw._cell_on is False
        assert hw._potential == 0.0
        assert hw._current == 0.0


# ---------------------------------------------------------------------------
# Connect / Disconnect
# ---------------------------------------------------------------------------


class TestConnectDisconnect:
    """Test connect and disconnect lifecycle."""

    def test_connect(self):
        hw = MockHardware()
        hw.connect()
        assert hw._connected is True

    def test_disconnect(self):
        hw = MockHardware()
        hw.connect()
        hw.disconnect()
        assert hw._connected is False

    def test_disconnect_without_connect(self):
        hw = MockHardware()
        hw.disconnect()
        assert hw._connected is False


# ---------------------------------------------------------------------------
# Cell On/Off
# ---------------------------------------------------------------------------


class TestCellControl:
    """Test cell on/off."""

    def test_cell_on(self):
        hw = MockHardware()
        hw.cell_on()
        assert hw._cell_on is True

    def test_cell_off(self):
        hw = MockHardware()
        hw.cell_on()
        hw.cell_off()
        assert hw._cell_on is False


# ---------------------------------------------------------------------------
# Potential / Current
# ---------------------------------------------------------------------------


class TestPotentialCurrent:
    """Test potential and current reading."""

    def test_set_potential(self):
        hw = MockHardware()
        hw.set_potential(0.75)
        assert hw._potential == 0.75

    def test_read_potential_near_set_value(self):
        hw = MockHardware()
        hw.set_potential(1.0)
        # Has Gaussian noise with sigma=1e-4, so should be within +/-0.01
        for _ in range(10):
            val = hw.read_potential()
            assert abs(val - 1.0) < 0.01

    def test_read_current_near_zero(self):
        hw = MockHardware()
        # Default current is 0.0, noise sigma=1e-6
        for _ in range(10):
            val = hw.read_current()
            assert abs(val) < 0.001


# ---------------------------------------------------------------------------
# run_cv
# ---------------------------------------------------------------------------


class TestRunCV:
    """Test cyclic voltammetry simulation."""

    def test_returns_dict(self):
        hw = MockHardware()
        result = hw.run_cv()
        assert isinstance(result, dict)

    def test_has_expected_keys(self):
        hw = MockHardware()
        result = hw.run_cv()
        assert "potentials_V" in result
        assert "currents_A" in result

    def test_returns_100_points(self):
        hw = MockHardware()
        result = hw.run_cv()
        assert len(result["potentials_V"]) == 100
        assert len(result["currents_A"]) == 100

    def test_potentials_are_list_of_floats(self):
        hw = MockHardware()
        result = hw.run_cv()
        assert all(isinstance(v, float) for v in result["potentials_V"])

    def test_currents_are_list_of_floats(self):
        hw = MockHardware()
        result = hw.run_cv()
        assert all(isinstance(v, float) for v in result["currents_A"])

    def test_custom_vertex_values(self):
        hw = MockHardware()
        result = hw.run_cv(vertex1=-0.5, vertex2=2.0)
        potentials = result["potentials_V"]
        # All potentials should be between vertex1 and vertex2 (with noise)
        assert all(-0.6 <= v <= 2.1 for v in potentials)

    def test_same_length_arrays(self):
        hw = MockHardware()
        result = hw.run_cv()
        assert len(result["potentials_V"]) == len(result["currents_A"])


# ---------------------------------------------------------------------------
# run_eis
# ---------------------------------------------------------------------------


class TestRunEIS:
    """Test electrochemical impedance spectroscopy simulation."""

    def test_returns_dict(self):
        hw = MockHardware()
        result = hw.run_eis()
        assert isinstance(result, dict)

    def test_has_expected_keys(self):
        hw = MockHardware()
        result = hw.run_eis()
        assert "Z_real" in result
        assert "Z_imag" in result
        assert "freq_Hz" in result

    def test_arrays_same_length(self):
        hw = MockHardware()
        result = hw.run_eis()
        assert len(result["Z_real"]) == len(result["Z_imag"]) == len(result["freq_Hz"])

    def test_values_are_numeric(self):
        hw = MockHardware()
        result = hw.run_eis()
        assert all(isinstance(v, (int, float)) for v in result["Z_real"])
        assert all(isinstance(v, (int, float)) for v in result["Z_imag"])
        assert all(isinstance(v, (int, float)) for v in result["freq_Hz"])


# ---------------------------------------------------------------------------
# run_ocp
# ---------------------------------------------------------------------------


class TestRunOCP:
    """Test open circuit potential measurement."""

    def test_returns_dict(self):
        hw = MockHardware()
        result = hw.run_ocp()
        assert isinstance(result, dict)

    def test_has_ocp_key(self):
        hw = MockHardware()
        result = hw.run_ocp()
        assert "ocp_V" in result

    def test_ocp_is_numeric(self):
        hw = MockHardware()
        result = hw.run_ocp()
        assert isinstance(result["ocp_V"], float)

    def test_ocp_near_expected_value(self):
        hw = MockHardware()
        # OCP is 0.05 +/- gauss(0, 0.01), should be within +/-0.1
        for _ in range(10):
            result = hw.run_ocp()
            assert abs(result["ocp_V"] - 0.05) < 0.1


# ---------------------------------------------------------------------------
# run_hold (chronoamperometry)
# ---------------------------------------------------------------------------


class TestRunHold:
    """Test potentiostatic hold (chronoamperometry)."""

    def test_returns_dict(self):
        hw = MockHardware()
        result = hw.run_hold()
        assert isinstance(result, dict)

    def test_has_expected_keys(self):
        hw = MockHardware()
        result = hw.run_hold()
        assert "current_A" in result
        assert "potential_V" in result

    def test_potential_echoes_input(self):
        hw = MockHardware()
        result = hw.run_hold(potential=1.23)
        assert result["potential_V"] == 1.23

    def test_default_potential(self):
        hw = MockHardware()
        result = hw.run_hold()
        assert result["potential_V"] == 0.5


# ---------------------------------------------------------------------------
# run_lsv
# ---------------------------------------------------------------------------


class TestRunLSV:
    """Test linear sweep voltammetry."""

    def test_returns_dict(self):
        hw = MockHardware()
        result = hw.run_lsv()
        assert isinstance(result, dict)

    def test_has_expected_keys(self):
        hw = MockHardware()
        result = hw.run_lsv()
        assert "potentials_V" in result
        assert "currents_A" in result

    def test_arrays_same_length(self):
        hw = MockHardware()
        result = hw.run_lsv()
        assert len(result["potentials_V"]) == len(result["currents_A"])

    def test_values_are_lists(self):
        hw = MockHardware()
        result = hw.run_lsv()
        assert isinstance(result["potentials_V"], list)
        assert isinstance(result["currents_A"], list)


# ---------------------------------------------------------------------------
# run_galvanostatic
# ---------------------------------------------------------------------------


class TestRunGalvanostatic:
    """Test galvanostatic hold."""

    def test_returns_dict(self):
        hw = MockHardware()
        result = hw.run_galvanostatic()
        assert isinstance(result, dict)

    def test_has_expected_keys(self):
        hw = MockHardware()
        result = hw.run_galvanostatic()
        assert "potential_V" in result
        assert "current_A" in result

    def test_current_echoes_input(self):
        hw = MockHardware()
        result = hw.run_galvanostatic(current=0.05)
        assert result["current_A"] == 0.05


# ---------------------------------------------------------------------------
# Other techniques
# ---------------------------------------------------------------------------


class TestOtherTechniques:
    """Test remaining technique methods."""

    def test_run_dpv(self):
        hw = MockHardware()
        result = hw.run_dpv()
        assert "potentials_V" in result
        assert "currents_A" in result
        assert len(result["potentials_V"]) == len(result["currents_A"])

    def test_run_swv(self):
        hw = MockHardware()
        result = hw.run_swv()
        assert "potentials_V" in result
        assert "currents_A" in result

    def test_run_gcd(self):
        hw = MockHardware()
        result = hw.run_gcd()
        assert "time_s" in result
        assert "potential_V" in result

    def test_run_cc(self):
        hw = MockHardware()
        result = hw.run_cc()
        assert "charge_C" in result
        assert "time_s" in result

    def test_run_stripping(self):
        hw = MockHardware()
        result = hw.run_stripping()
        assert "potentials_V" in result
        assert "currents_A" in result

    def test_run_purge(self):
        hw = MockHardware()
        result = hw.run_purge()
        assert "gas" in result
        assert "duration_s" in result

    def test_run_purge_custom_gas(self):
        hw = MockHardware()
        result = hw.run_purge(gas="O2", duration=600)
        assert result["gas"] == "O2"
        assert result["duration_s"] == 600
