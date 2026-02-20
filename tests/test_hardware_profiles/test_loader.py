"""Tests for ecproc.hardware_profiles.loader - hardware profile loading."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ecproc.hardware_profiles.loader import (
    list_profiles,
    load_profile,
    load_profile_file,
)

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# load_profile
# ---------------------------------------------------------------------------


class TestLoadProfile:
    """Test loading built-in hardware profiles by name."""

    def test_load_mock_returns_dict(self):
        profile = load_profile("mock")
        assert isinstance(profile, dict)

    def test_load_gamry_1010e_returns_dict(self):
        profile = load_profile("gamry_1010e")
        assert isinstance(profile, dict)

    def test_mock_has_hardware_id(self):
        profile = load_profile("mock")
        assert "hardware_id" in profile
        assert profile["hardware_id"] == "mock"

    def test_gamry_has_hardware_id(self):
        profile = load_profile("gamry_1010e")
        assert profile["hardware_id"] == "gamry_1010e"

    def test_mock_has_manufacturer(self):
        profile = load_profile("mock")
        assert "manufacturer" in profile
        assert isinstance(profile["manufacturer"], str)

    def test_gamry_has_manufacturer(self):
        profile = load_profile("gamry_1010e")
        assert "manufacturer" in profile
        assert profile["manufacturer"] == "Gamry Instruments"

    def test_mock_has_capabilities(self):
        profile = load_profile("mock")
        assert "capabilities" in profile
        assert isinstance(profile["capabilities"], dict)

    def test_gamry_has_capabilities(self):
        profile = load_profile("gamry_1010e")
        assert "capabilities" in profile

    def test_unknown_profile_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="Hardware profile not found"):
            load_profile("nonexistent_potentiostat_xyz")

    def test_unknown_profile_error_contains_name(self):
        with pytest.raises(FileNotFoundError, match="does_not_exist"):
            load_profile("does_not_exist")


# ---------------------------------------------------------------------------
# Profile capabilities structure
# ---------------------------------------------------------------------------


class TestProfileCapabilities:
    """Test the capabilities structure of profiles."""

    def test_mock_capabilities_have_techniques(self):
        profile = load_profile("mock")
        caps = profile["capabilities"]
        assert "techniques" in caps
        assert isinstance(caps["techniques"], list)

    def test_gamry_capabilities_have_techniques(self):
        profile = load_profile("gamry_1010e")
        caps = profile["capabilities"]
        assert "techniques" in caps
        assert isinstance(caps["techniques"], list)

    def test_mock_techniques_include_cv(self):
        profile = load_profile("mock")
        techniques = profile["capabilities"]["techniques"]
        assert "cv" in techniques

    def test_mock_techniques_include_eis(self):
        profile = load_profile("mock")
        techniques = profile["capabilities"]["techniques"]
        assert "eis" in techniques

    def test_gamry_techniques_include_cv(self):
        profile = load_profile("gamry_1010e")
        techniques = profile["capabilities"]["techniques"]
        assert "cv" in techniques

    def test_mock_has_potential_limits(self):
        profile = load_profile("mock")
        caps = profile["capabilities"]
        assert "max_potential_v" in caps
        assert "min_potential_v" in caps

    def test_mock_has_current_limits(self):
        profile = load_profile("mock")
        caps = profile["capabilities"]
        assert "max_current_a" in caps
        assert "min_current_a" in caps

    def test_mock_has_eis_config(self):
        profile = load_profile("mock")
        caps = profile["capabilities"]
        assert "eis" in caps
        eis = caps["eis"]
        assert "frequency_range_hz" in eis
        assert "max_amplitude_v" in eis


# ---------------------------------------------------------------------------
# load_profile_file
# ---------------------------------------------------------------------------


class TestLoadProfileFile:
    """Test loading hardware profiles from arbitrary file paths."""

    def test_load_from_file(self, tmp_path: Path):
        profile_data = {
            "hardware_id": "test_hw",
            "manufacturer": "Test Corp",
            "capabilities": {"techniques": ["cv"]},
        }
        filepath = tmp_path / "test_hw.json"
        filepath.write_text(json.dumps(profile_data), encoding="utf-8")

        loaded = load_profile_file(filepath)
        assert loaded == profile_data

    def test_load_from_string_path(self, tmp_path: Path):
        profile_data = {"hardware_id": "x", "manufacturer": "y", "capabilities": {}}
        filepath = tmp_path / "x.json"
        filepath.write_text(json.dumps(profile_data), encoding="utf-8")

        loaded = load_profile_file(str(filepath))
        assert loaded["hardware_id"] == "x"

    def test_nonexistent_file_raises(self):
        with pytest.raises(Exception):
            load_profile_file("/nonexistent/path/hw.json")


# ---------------------------------------------------------------------------
# list_profiles
# ---------------------------------------------------------------------------


class TestListProfiles:
    """Test listing available profiles."""

    def test_returns_list(self):
        profiles = list_profiles()
        assert isinstance(profiles, list)

    def test_includes_mock(self):
        profiles = list_profiles()
        assert "mock" in profiles

    def test_includes_gamry_1010e(self):
        profiles = list_profiles()
        assert "gamry_1010e" in profiles

    def test_all_entries_are_strings(self):
        profiles = list_profiles()
        assert all(isinstance(p, str) for p in profiles)

    def test_all_listed_profiles_are_loadable(self):
        """Every profile name from list_profiles() should be loadable."""
        for name in list_profiles():
            profile = load_profile(name)
            assert isinstance(profile, dict)
