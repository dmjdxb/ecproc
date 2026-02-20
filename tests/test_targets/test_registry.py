"""Tests for ecproc.targets.registry - target plugin registry."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from ecproc.targets.base import CompilationResult, ECProcTarget, ExecutionResult
from ecproc.targets.registry import TargetRegistry, get_registry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class DummyTarget(ECProcTarget):
    """Concrete target for testing."""

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def version(self) -> str:
        return "0.1.0"

    def capabilities(self) -> dict[str, Any]:
        return {"techniques": ["cv"]}

    def compile(self, ir: Any) -> CompilationResult:
        return CompilationResult(target=self.name, output=ir)

    def execute(self, compiled: CompilationResult) -> ExecutionResult:
        return ExecutionResult(success=True, target=self.name)


class AnotherTarget(ECProcTarget):
    """A second concrete target for testing."""

    @property
    def name(self) -> str:
        return "another"

    @property
    def version(self) -> str:
        return "2.0.0"

    def capabilities(self) -> dict[str, Any]:
        return {"techniques": ["eis"]}

    def compile(self, ir: Any) -> CompilationResult:
        return CompilationResult(target=self.name, output=ir)

    def execute(self, compiled: CompilationResult) -> ExecutionResult:
        return ExecutionResult(success=True, target=self.name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTargetRegistryCreation:
    """Test TargetRegistry instantiation."""

    def test_empty_on_creation(self):
        registry = TargetRegistry()
        assert registry.list_targets() == []

    def test_internal_dict_is_empty(self):
        registry = TargetRegistry()
        assert len(registry._targets) == 0


class TestRegister:
    """Test registering targets."""

    def test_register_single_target(self):
        registry = TargetRegistry()
        target = DummyTarget()
        registry.register(target)
        assert "dummy" in registry.list_targets()

    def test_register_multiple_targets(self):
        registry = TargetRegistry()
        registry.register(DummyTarget())
        registry.register(AnotherTarget())
        names = registry.list_targets()
        assert "dummy" in names
        assert "another" in names
        assert len(names) == 2

    def test_register_overwrites_same_name(self):
        registry = TargetRegistry()
        target1 = DummyTarget()
        target2 = DummyTarget()
        registry.register(target1)
        registry.register(target2)
        assert len(registry.list_targets()) == 1
        assert registry.get("dummy") is target2


class TestGet:
    """Test retrieving registered targets."""

    def test_get_registered_target(self):
        registry = TargetRegistry()
        target = DummyTarget()
        registry.register(target)
        result = registry.get("dummy")
        assert result is target

    def test_get_returns_correct_target_among_many(self):
        registry = TargetRegistry()
        t1 = DummyTarget()
        t2 = AnotherTarget()
        registry.register(t1)
        registry.register(t2)
        assert registry.get("dummy") is t1
        assert registry.get("another") is t2

    def test_get_unknown_target_returns_none(self):
        registry = TargetRegistry()
        result = registry.get("nonexistent")
        assert result is None

    def test_get_unknown_after_registrations(self):
        registry = TargetRegistry()
        registry.register(DummyTarget())
        assert registry.get("not_here") is None


class TestListTargets:
    """Test listing registered target names."""

    def test_empty_registry(self):
        registry = TargetRegistry()
        assert registry.list_targets() == []

    def test_list_after_single_registration(self):
        registry = TargetRegistry()
        registry.register(DummyTarget())
        assert registry.list_targets() == ["dummy"]

    def test_list_returns_new_list(self):
        registry = TargetRegistry()
        registry.register(DummyTarget())
        names1 = registry.list_targets()
        names2 = registry.list_targets()
        assert names1 == names2
        assert names1 is not names2  # Returns a copy


class TestDiscover:
    """Test plugin discovery via entry points."""

    def test_discover_with_no_plugins(self):
        """discover() runs without error even when no plugins exist."""
        registry = TargetRegistry()
        registry.discover()
        # Should not raise; may or may not find plugins

    @patch("ecproc.targets.registry.importlib.metadata.entry_points")
    def test_discover_loads_entry_points(self, mock_eps):
        """discover() loads and registers entry point targets."""
        mock_ep = MagicMock()
        mock_ep.load.return_value = DummyTarget

        # Simulate entry_points() returning a dict-like with select
        mock_result = MagicMock()
        mock_result.select.return_value = [mock_ep]
        mock_result.get.return_value = []
        mock_result.__contains__ = lambda self, key: True
        # hasattr(eps, "select") should be True
        mock_eps.return_value = mock_result

        registry = TargetRegistry()
        registry.discover()

        mock_ep.load.assert_called_once()
        assert "dummy" in registry.list_targets()

    @patch("ecproc.targets.registry.importlib.metadata.entry_points")
    def test_discover_handles_load_error(self, mock_eps):
        """discover() swallows errors from individual entry points."""
        mock_ep = MagicMock()
        mock_ep.load.side_effect = ImportError("bad plugin")

        mock_result = MagicMock()
        mock_result.select.return_value = [mock_ep]
        mock_result.get.return_value = []
        mock_eps.return_value = mock_result

        registry = TargetRegistry()
        registry.discover()  # Should not raise
        assert registry.list_targets() == []

    @patch("ecproc.targets.registry.importlib.metadata.entry_points")
    def test_discover_handles_entry_points_error(self, mock_eps):
        """discover() swallows top-level entry_points() errors."""
        mock_eps.side_effect = Exception("metadata broken")

        registry = TargetRegistry()
        registry.discover()  # Should not raise
        assert registry.list_targets() == []


class TestGetRegistry:
    """Test the module-level get_registry() accessor."""

    def test_returns_target_registry(self):
        registry = get_registry()
        assert isinstance(registry, TargetRegistry)

    def test_returns_same_instance(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2
