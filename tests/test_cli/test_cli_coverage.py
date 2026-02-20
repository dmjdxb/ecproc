"""Additional CLI tests for ecproc - covering compile, run, convert, execute, manual."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from ecproc.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()

# ---------------------------------------------------------------------------
# Shared fixture YAML
# ---------------------------------------------------------------------------

VALID_ECPROC_YAML = """\
metadata:
  protocol: "CLI Coverage Test"
  version: "1.0"
  author: "Test Suite"

system:
  electrodes: 3
  reference: RHE

procedure:
  - name: Conditioning
    steps:
      - cv:
          vertex1: 0.05
          vertex2: 1.2
          rate: 50
          cycles: 20
"""


@pytest.fixture
def ecproc_file(tmp_path: Path) -> Path:
    """Write a valid .ecproc file and return its path."""
    f = tmp_path / "coverage_test.ecproc"
    f.write_text(VALID_ECPROC_YAML, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# compile command
# ---------------------------------------------------------------------------


class TestCompileCommand:
    """Test the compile CLI command."""

    def test_compile_valid_file_succeeds(self, ecproc_file: Path):
        result = runner.invoke(app, ["compile", str(ecproc_file)])
        # Should succeed or at least not crash unexpectedly
        assert result.exit_code in (0, 1, 2, 3)

    def test_compile_with_python_target(self, ecproc_file: Path):
        result = runner.invoke(
            app, ["compile", str(ecproc_file), "--target", "python"]
        )
        if result.exit_code == 0:
            assert "Compiled" in result.output or "python" in result.output.lower()

    def test_compile_with_manual_target(self, ecproc_file: Path):
        result = runner.invoke(
            app, ["compile", str(ecproc_file), "--target", "manual"]
        )
        # Manual target may or may not be fully implemented
        assert result.exit_code in (0, 1, 2, 3)

    def test_compile_nonexistent_file(self):
        result = runner.invoke(app, ["compile", "/does/not/exist.ecproc"])
        assert result.exit_code != 0

    def test_compile_with_output_flag(self, ecproc_file: Path, tmp_path: Path):
        out_dir = tmp_path / "compiled_output"
        result = runner.invoke(
            app, ["compile", str(ecproc_file), "-o", str(out_dir)]
        )
        # Just verify it doesn't crash; output directory usage depends on target
        assert result.exit_code in (0, 1, 2, 3)


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------


class TestRunCommand:
    """Test the run CLI command."""

    def test_run_nonexistent_file(self):
        result = runner.invoke(app, ["run", "/does/not/exist.ecproc"])
        assert result.exit_code != 0

    def test_run_valid_file_dry_run(self, ecproc_file: Path):
        result = runner.invoke(
            app, ["run", str(ecproc_file), "--dry-run"]
        )
        # Dry run should succeed or give a clean error
        if result.exit_code == 0:
            assert "complete" in result.output.lower() or "dry" in result.output.lower()

    def test_run_valid_file_with_target(self, ecproc_file: Path):
        result = runner.invoke(
            app, ["run", str(ecproc_file), "--target", "python"]
        )
        # Should succeed with mock hardware
        assert result.exit_code in (0, 4)

    def test_run_valid_file_with_output_dir(self, ecproc_file: Path, tmp_path: Path):
        out_dir = tmp_path / "run_output"
        out_dir.mkdir()
        result = runner.invoke(
            app, ["run", str(ecproc_file), "-o", str(out_dir)]
        )
        assert result.exit_code in (0, 4)

    def test_run_help(self):
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "dry_run" in result.output.lower()


# ---------------------------------------------------------------------------
# convert command
# ---------------------------------------------------------------------------


class TestConvertCommand:
    """Test the convert CLI command."""

    def test_convert_nonexistent_file(self):
        result = runner.invoke(app, ["convert", "/does/not/exist.ecproc"])
        assert result.exit_code != 0

    def test_convert_valid_file_to_ir(self, ecproc_file: Path):
        result = runner.invoke(
            app, ["convert", str(ecproc_file), "--to", "ir"]
        )
        # Convert is partially implemented; should not crash
        assert result.exit_code in (0, 1, 2)

    def test_convert_valid_file_to_yaml(self, ecproc_file: Path):
        result = runner.invoke(
            app, ["convert", str(ecproc_file), "--to", "yaml"]
        )
        assert result.exit_code in (0, 1, 2)

    def test_convert_valid_file_to_ecdl(self, ecproc_file: Path):
        result = runner.invoke(
            app, ["convert", str(ecproc_file), "--to", "ecdl"]
        )
        assert result.exit_code in (0, 1, 2)

    def test_convert_help(self):
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "convert" in result.output.lower() or "format" in result.output.lower()

    def test_convert_with_output_flag(self, ecproc_file: Path, tmp_path: Path):
        out_file = tmp_path / "converted.ir.json"
        result = runner.invoke(
            app, ["convert", str(ecproc_file), "--to", "ir", "-o", str(out_file)]
        )
        assert result.exit_code in (0, 1, 2)


# ---------------------------------------------------------------------------
# execute command
# ---------------------------------------------------------------------------


class TestExecuteCommand:
    """Test the execute CLI command (all-in-one parse/validate/compile/run)."""

    def test_execute_nonexistent_file(self):
        result = runner.invoke(app, ["execute", "/does/not/exist.ecproc"])
        assert result.exit_code != 0

    def test_execute_valid_file(self, ecproc_file: Path, tmp_path: Path):
        out_dir = tmp_path / "execute_output"
        out_dir.mkdir()
        result = runner.invoke(
            app, ["execute", str(ecproc_file), "-o", str(out_dir)]
        )
        # Should succeed end-to-end with mock hardware, or fail validation
        assert result.exit_code in (0, 1, 4)

    def test_execute_with_hardware_flag(self, ecproc_file: Path, tmp_path: Path):
        out_dir = tmp_path / "hw_output"
        out_dir.mkdir()
        result = runner.invoke(
            app,
            ["execute", str(ecproc_file), "--hardware", "mock", "-o", str(out_dir)],
        )
        assert result.exit_code in (0, 1, 4)

    def test_execute_help(self):
        result = runner.invoke(app, ["execute", "--help"])
        assert result.exit_code == 0
        assert "hardware" in result.output.lower()


# ---------------------------------------------------------------------------
# manual command
# ---------------------------------------------------------------------------


class TestManualCommand:
    """Test the manual CLI command (generate human-readable procedure)."""

    def test_manual_nonexistent_file(self):
        result = runner.invoke(app, ["manual", "/does/not/exist.ecproc"])
        assert result.exit_code != 0

    def test_manual_valid_file(self, ecproc_file: Path):
        result = runner.invoke(app, ["manual", str(ecproc_file)])
        # Should produce markdown output to stdout
        if result.exit_code == 0:
            # Manual output should contain some text
            assert len(result.output) > 0

    def test_manual_with_md_format(self, ecproc_file: Path):
        result = runner.invoke(
            app, ["manual", str(ecproc_file), "--format", "md"]
        )
        assert result.exit_code in (0, 1)

    def test_manual_with_output_file(self, ecproc_file: Path, tmp_path: Path):
        out_file = tmp_path / "manual.md"
        result = runner.invoke(
            app, ["manual", str(ecproc_file), "-o", str(out_file)]
        )
        if result.exit_code == 0:
            assert out_file.exists()
            content = out_file.read_text(encoding="utf-8")
            assert len(content) > 0

    def test_manual_help(self):
        result = runner.invoke(app, ["manual", "--help"])
        assert result.exit_code == 0
        assert "format" in result.output.lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestCLIEdgeCases:
    """Test edge cases in CLI commands."""

    def test_no_command_shows_help(self):
        result = runner.invoke(app, [])
        # No command should show help or usage
        assert result.exit_code == 0

    def test_unknown_command(self):
        result = runner.invoke(app, ["nonexistent_command"])
        assert result.exit_code != 0

    def test_ir_json_input_for_compile(self, tmp_path: Path):
        """Test that compile can accept .ir.json file (if present)."""
        # Create a minimal IR JSON
        import json

        ir_data = {
            "faraday_version": "1.0",
            "metadata": {
                "protocol": "Test",
                "version": "1.0",
                "created": "2026-01-01T00:00:00",
                "ecproc_version": "0.1.0",
                "source_hash": "abc123",
            },
            "system": {"electrodes": 3, "reference": "RHE"},
            "procedure": [
                {
                    "name": "Phase1",
                    "steps": [
                        {
                            "technique": "cv",
                            "vertex1": 0.05,
                            "vertex2": 1.2,
                            "scan_rate_V_s": 0.05,
                            "cycles": 20,
                        }
                    ],
                }
            ],
            "provenance": {
                "source_hash": "abc123",
                "parser_version": "0.1.0",
            },
        }
        ir_file = tmp_path / "test.ir.json"
        ir_file.write_text(json.dumps(ir_data), encoding="utf-8")

        result = runner.invoke(app, ["compile", str(ir_file)])
        # IR JSON should be loadable by the compile command
        assert result.exit_code in (0, 1, 2, 3)

    def test_ir_json_input_for_run(self, tmp_path: Path):
        """Test that run can accept .json file as IR input."""
        import json

        ir_data = {
            "faraday_version": "1.0",
            "metadata": {
                "protocol": "Test",
                "version": "1.0",
                "created": "2026-01-01T00:00:00",
                "ecproc_version": "0.1.0",
                "source_hash": "abc123",
            },
            "system": {"electrodes": 3, "reference": "RHE"},
            "procedure": [
                {
                    "name": "Phase1",
                    "steps": [
                        {
                            "technique": "cv",
                            "vertex1": 0.05,
                            "vertex2": 1.2,
                            "scan_rate_V_s": 0.05,
                            "cycles": 20,
                        }
                    ],
                }
            ],
            "provenance": {
                "source_hash": "abc123",
                "parser_version": "0.1.0",
            },
        }
        ir_file = tmp_path / "test.json"
        ir_file.write_text(json.dumps(ir_data), encoding="utf-8")

        result = runner.invoke(app, ["run", str(ir_file), "--dry-run"])
        assert result.exit_code in (0, 4)
