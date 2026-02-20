"""Manual instruction generation target."""

from __future__ import annotations

from typing import Any

from ecproc.ir.schema import FaradayIR
from ecproc.targets.base import CompilationResult, ECProcTarget, ExecutionResult
from ecproc.targets.manual.compiler import compile_to_manual


class ManualTarget(ECProcTarget):
    """Concrete target that compiles IR to human-readable manual instructions."""

    @property
    def name(self) -> str:
        return "manual"

    @property
    def version(self) -> str:
        return "0.1.0"

    def capabilities(self) -> dict[str, Any]:
        return {
            "output_formats": ["markdown", "pdf"],
            "techniques": [
                "cv", "lsv", "eis", "ocp", "hold",
                "galvanostatic", "dpv", "swv", "gcd",
                "cc", "stripping", "purge",
            ],
            "loops": True,
            "checkpoints": True,
        }

    def compile(self, ir: Any) -> CompilationResult:
        if not isinstance(ir, FaradayIR):
            ir = FaradayIR.model_validate(ir)
        return compile_to_manual(ir)

    def execute(self, compiled: CompilationResult) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            target="manual",
            observations=[{"manual_sections": len(compiled.output)}],
        )
