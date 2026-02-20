"""Tests for ecproc.targets.python.runtime - execution engine."""

from __future__ import annotations

from unittest.mock import MagicMock

from ecproc.targets.base import ExecutionResult
from ecproc.targets.python.runtime import PythonRuntime


def _make_mock_hardware(name: str = "mock_potentiostat") -> MagicMock:
    """Create a mock hardware object with the standard interface."""
    hw = MagicMock()
    hw.name = name
    hw.connect = MagicMock()
    hw.disconnect = MagicMock()
    hw.run_cv = MagicMock(return_value={"voltage": [0.0, 1.0], "current": [0.0, 0.01]})
    hw.run_eis = MagicMock(return_value={"z_real": [100], "z_imag": [-50]})
    hw.run_ocp = MagicMock(return_value={"potential": 0.85})
    return hw


def _simple_instructions() -> list[dict]:
    """Create simple compiled instructions for testing."""
    return [
        {"type": "phase_start", "name": "Test Phase", "setup": None},
        {
            "type": "step",
            "technique": "cv",
            "tag": "test_cv",
            "extract": None,
            "vendor_flags": None,
            "parameters": {"vertex1": 0.05, "vertex2": 1.2, "rate": 0.05, "cycles": 3},
        },
        {"type": "phase_end", "name": "Test Phase"},
    ]


class TestPythonRuntime:
    """Test PythonRuntime execution engine."""

    def test_runtime_creation(self):
        hw = _make_mock_hardware()
        runtime = PythonRuntime(hw)
        assert runtime.hardware is hw
        assert runtime.observations == []
        assert runtime.data_files == []

    def test_execute_returns_execution_result(self):
        hw = _make_mock_hardware()
        runtime = PythonRuntime(hw)
        result = runtime.execute(_simple_instructions())
        assert isinstance(result, ExecutionResult)

    def test_execute_success(self):
        hw = _make_mock_hardware()
        runtime = PythonRuntime(hw)
        result = runtime.execute(_simple_instructions())
        assert result.success is True
        assert result.target == "python"
        assert result.errors == []

    def test_execute_calls_connect_and_disconnect(self):
        hw = _make_mock_hardware()
        runtime = PythonRuntime(hw)
        runtime.execute(_simple_instructions())
        hw.connect.assert_called_once()
        hw.disconnect.assert_called_once()

    def test_execute_calls_hardware_method(self):
        hw = _make_mock_hardware()
        runtime = PythonRuntime(hw)
        runtime.execute(_simple_instructions())
        hw.run_cv.assert_called_once()

    def test_execute_records_observations_with_tag(self):
        hw = _make_mock_hardware()
        runtime = PythonRuntime(hw)
        runtime.execute(_simple_instructions())
        assert len(runtime.observations) >= 1
        obs = runtime.observations[0]
        assert obs["tag"] == "test_cv"
        assert obs["technique"] == "cv"

    def test_dry_run_skips_hardware(self):
        hw = _make_mock_hardware()
        runtime = PythonRuntime(hw)
        result = runtime.execute(_simple_instructions(), dry_run=True)
        assert result.success is True
        hw.connect.assert_not_called()
        hw.disconnect.assert_not_called()
        hw.run_cv.assert_not_called()

    def test_dry_run_produces_no_observations(self):
        hw = _make_mock_hardware()
        runtime = PythonRuntime(hw)
        runtime.execute(_simple_instructions(), dry_run=True)
        assert runtime.observations == []

    def test_execute_has_timestamps(self):
        hw = _make_mock_hardware()
        runtime = PythonRuntime(hw)
        result = runtime.execute(_simple_instructions())
        assert result.started != ""
        assert result.completed != ""

    def test_execute_reports_hardware_name(self):
        hw = _make_mock_hardware(name="biologic_sp200")
        runtime = PythonRuntime(hw)
        result = runtime.execute(_simple_instructions())
        assert result.hardware == "biologic_sp200"

    def test_execute_handles_hardware_error(self):
        hw = _make_mock_hardware()
        hw.connect.side_effect = RuntimeError("Connection failed")
        runtime = PythonRuntime(hw)
        result = runtime.execute(_simple_instructions())
        assert result.success is False
        assert len(result.errors) > 0
        assert "Connection failed" in result.errors[0]

    def test_execute_loop_instruction(self):
        hw = _make_mock_hardware()
        runtime = PythonRuntime(hw)
        instructions = [
            {"type": "phase_start", "name": "Loop Phase", "setup": None},
            {
                "type": "loop",
                "count": 3,
                "steps": [
                    {
                        "type": "step",
                        "technique": "cv",
                        "tag": None,
                        "extract": None,
                        "vendor_flags": None,
                        "parameters": {"vertex1": 0.0, "vertex2": 1.0},
                    }
                ],
                "stop_if": None,
            },
            {"type": "phase_end", "name": "Loop Phase"},
        ]
        runtime.execute(instructions)
        assert hw.run_cv.call_count == 3
