"""Python execution target."""

from __future__ import annotations

from typing import Any

from ecproc.ir.schema import FaradayIR
from ecproc.targets.base import CompilationResult, ECProcTarget, ExecutionResult
from ecproc.targets.python.compiler import compile_to_python
from ecproc.targets.python.runtime import PythonRuntime


class PythonTarget(ECProcTarget):
    """Concrete target that compiles and executes via Python."""

    @property
    def name(self) -> str:
        return "python"

    @property
    def version(self) -> str:
        return "0.1.0"

    def capabilities(self) -> dict[str, Any]:
        return {
            "techniques": [
                "cv", "lsv", "eis", "ocp", "hold",
                "galvanostatic", "dpv", "swv", "gcd",
                "cc", "stripping", "purge",
            ],
            "hardware": ["mock", "gamry", "biologic", "palmsens", "pine"],
            "loops": True,
            "checkpoints": True,
        }

    def compile(self, ir: Any) -> CompilationResult:
        if not isinstance(ir, FaradayIR):
            ir = FaradayIR.model_validate(ir)
        return compile_to_python(ir)

    def execute(self, compiled: CompilationResult) -> ExecutionResult:
        from ecproc.targets.python.hardware.mock import MockHardware

        runtime = PythonRuntime(hardware=MockHardware())
        return runtime.execute(compiled.output)
