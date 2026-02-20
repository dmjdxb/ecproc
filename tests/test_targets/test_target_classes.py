"""Tests for concrete PythonTarget and ManualTarget classes."""

from __future__ import annotations

from ecproc.targets.base import CompilationResult, ECProcTarget, ExecutionResult
from ecproc.targets.manual import ManualTarget
from ecproc.targets.python import PythonTarget


class TestPythonTarget:
    """Test PythonTarget concrete implementation."""

    def test_is_ecproc_target(self) -> None:
        target = PythonTarget()
        assert isinstance(target, ECProcTarget)

    def test_name(self) -> None:
        assert PythonTarget().name == "python"

    def test_version(self) -> None:
        assert PythonTarget().version == "0.1.0"

    def test_capabilities_has_techniques(self) -> None:
        caps = PythonTarget().capabilities()
        assert "techniques" in caps
        assert "cv" in caps["techniques"]

    def test_compile_returns_compilation_result(self, simple_faraday_ir) -> None:  # type: ignore[no-untyped-def]
        target = PythonTarget()
        result = target.compile(simple_faraday_ir)
        assert isinstance(result, CompilationResult)
        assert result.target == "python"

    def test_execute_returns_execution_result(self, simple_faraday_ir) -> None:  # type: ignore[no-untyped-def]
        target = PythonTarget()
        compiled = target.compile(simple_faraday_ir)
        result = target.execute(compiled)
        assert isinstance(result, ExecutionResult)
        assert result.target == "python"
        assert result.success is True


class TestManualTarget:
    """Test ManualTarget concrete implementation."""

    def test_is_ecproc_target(self) -> None:
        target = ManualTarget()
        assert isinstance(target, ECProcTarget)

    def test_name(self) -> None:
        assert ManualTarget().name == "manual"

    def test_version(self) -> None:
        assert ManualTarget().version == "0.1.0"

    def test_capabilities_has_output_formats(self) -> None:
        caps = ManualTarget().capabilities()
        assert "output_formats" in caps
        assert "markdown" in caps["output_formats"]

    def test_compile_returns_compilation_result(self, simple_faraday_ir) -> None:  # type: ignore[no-untyped-def]
        target = ManualTarget()
        result = target.compile(simple_faraday_ir)
        assert isinstance(result, CompilationResult)
        assert result.target == "manual"

    def test_execute_returns_execution_result(self, simple_faraday_ir) -> None:  # type: ignore[no-untyped-def]
        target = ManualTarget()
        compiled = target.compile(simple_faraday_ir)
        result = target.execute(compiled)
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.target == "manual"
