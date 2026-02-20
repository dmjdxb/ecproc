"""Tests for ecproc.targets.python.data_handler - raw data file management."""

from __future__ import annotations

import json
from pathlib import Path

from ecproc.targets.python.data_handler import DataHandler

# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


class TestDataHandlerCreation:
    """Test DataHandler instantiation."""

    def test_creates_output_dir(self, tmp_path: Path):
        out = tmp_path / "data_out"
        _handler = DataHandler(out)
        assert out.exists()
        assert out.is_dir()

    def test_accepts_string_path(self, tmp_path: Path):
        out = str(tmp_path / "string_path")
        _handler = DataHandler(out)
        assert Path(out).exists()

    def test_existing_dir_ok(self, tmp_path: Path):
        _handler = DataHandler(tmp_path)
        assert tmp_path.exists()

    def test_files_initially_empty(self, tmp_path: Path):
        handler = DataHandler(tmp_path)
        assert handler.files == []


# ---------------------------------------------------------------------------
# save_step_data
# ---------------------------------------------------------------------------


class TestSaveStepData:
    """Test saving step data to files."""

    def test_saves_file(self, tmp_path: Path):
        handler = DataHandler(tmp_path)
        data = {"voltage": [0.0, 1.0], "current": [0.0, 0.01]}
        filepath = handler.save_step_data("phase1", "cv", data)
        assert Path(filepath).exists()

    def test_file_named_correctly(self, tmp_path: Path):
        handler = DataHandler(tmp_path)
        data = {"x": 1}
        filepath = handler.save_step_data("conditioning", "eis", data)
        assert "conditioning_eis.json" in filepath

    def test_file_contains_valid_json(self, tmp_path: Path):
        handler = DataHandler(tmp_path)
        data = {"potentials": [0.0, 0.5, 1.0], "currents": [0.0, 0.001, 0.01]}
        filepath = handler.save_step_data("test", "cv", data)
        loaded = json.loads(Path(filepath).read_text(encoding="utf-8"))
        assert loaded == data

    def test_tracks_saved_file(self, tmp_path: Path):
        handler = DataHandler(tmp_path)
        data = {"v": 1}
        filepath = handler.save_step_data("s1", "ocp", data)
        assert filepath in handler.files

    def test_multiple_saves(self, tmp_path: Path):
        handler = DataHandler(tmp_path)
        handler.save_step_data("p1", "cv", {"a": 1})
        handler.save_step_data("p2", "eis", {"b": 2})
        handler.save_step_data("p3", "lsv", {"c": 3})
        assert len(handler.files) == 3

    def test_data_with_special_types(self, tmp_path: Path):
        """Non-serializable types use str via default=str."""
        handler = DataHandler(tmp_path)
        from datetime import datetime
        data = {"timestamp": datetime(2026, 1, 1)}
        filepath = handler.save_step_data("special", "ocp", data)
        loaded = json.loads(Path(filepath).read_text(encoding="utf-8"))
        assert isinstance(loaded["timestamp"], str)


# ---------------------------------------------------------------------------
# files property
# ---------------------------------------------------------------------------


class TestFilesProperty:
    """Test the files property."""

    def test_returns_list(self, tmp_path: Path):
        handler = DataHandler(tmp_path)
        assert isinstance(handler.files, list)

    def test_returns_copy(self, tmp_path: Path):
        handler = DataHandler(tmp_path)
        handler.save_step_data("t", "cv", {"x": 1})
        files1 = handler.files
        files2 = handler.files
        assert files1 == files2
        assert files1 is not files2  # Returns a copy

    def test_mutation_does_not_affect_internal(self, tmp_path: Path):
        handler = DataHandler(tmp_path)
        handler.save_step_data("t", "cv", {"x": 1})
        files = handler.files
        files.append("bogus.json")
        assert "bogus.json" not in handler.files
