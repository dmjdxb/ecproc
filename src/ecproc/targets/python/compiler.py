"""Python target compiler - IR to executable Python."""

from __future__ import annotations

from typing import Any

from ecproc.ir.schema import FaradayIR, IRLoop, IRStep
from ecproc.targets.base import CompilationResult


def compile_to_python(ir: FaradayIR) -> CompilationResult:
    """Compile Faraday IR to executable Python instructions."""
    instructions: list[dict[str, Any]] = []

    for phase in ir.procedure:
        instructions.append({"type": "phase_start", "name": phase.name, "setup": phase.setup})

        if phase.stabilize:
            instructions.append({"type": "stabilize", "conditions": phase.stabilize})

        for step in phase.steps:
            if isinstance(step, IRStep):
                instructions.append(_step_to_instruction(step))
            elif isinstance(step, IRLoop):
                instructions.append(_loop_to_instruction(step))

        if phase.teardown:
            instructions.append({"type": "phase_teardown", "teardown": phase.teardown})

        instructions.append({"type": "phase_end", "name": phase.name})

    return CompilationResult(target="python", output=instructions)


def _step_to_instruction(step: IRStep) -> dict[str, Any]:
    params = {k: v for k, v in step.model_dump().items()
              if k not in ("technique", "tag", "extract", "vendor_flags") and v is not None}
    return {
        "type": "step",
        "technique": step.technique,
        "tag": step.tag,
        "extract": step.extract,
        "vendor_flags": step.vendor_flags,
        "parameters": params,
    }


def _loop_to_instruction(loop: IRLoop) -> dict[str, Any]:
    steps = []
    for s in loop.steps:
        if isinstance(s, IRStep):
            steps.append(_step_to_instruction(s))
        elif isinstance(s, IRLoop):
            steps.append(_loop_to_instruction(s))
    return {
        "type": "loop",
        "count": loop.count,
        "steps": steps,
        "stop_if": loop.stop_if,
    }
