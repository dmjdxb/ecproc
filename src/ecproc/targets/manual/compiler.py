"""Manual target compiler - IR to structured instructions."""

from __future__ import annotations

from typing import Any

from ecproc.ir.schema import FaradayIR, IRLoop, IRPhase, IRStep
from ecproc.targets.base import CompilationResult


def compile_to_manual(ir: FaradayIR) -> CompilationResult:
    """Compile Faraday IR to structured manual instructions."""
    sections: list[dict[str, Any]] = []

    # Equipment section
    sections.append({
        "type": "equipment",
        "system": ir.system.model_dump(),
    })

    # Safety section
    if ir.safety:
        sections.append({
            "type": "safety",
            "constraints": ir.safety.model_dump(),
        })

    # Procedure steps
    for phase in ir.procedure:
        sections.append(_phase_to_section(phase))

    return CompilationResult(target="manual", output=sections)


def _phase_to_section(phase: IRPhase) -> dict[str, Any]:
    steps = []
    for s in phase.steps:
        if isinstance(s, IRStep):
            steps.append(_step_to_instruction(s))
        elif isinstance(s, IRLoop):
            steps.append(_loop_to_instruction(s))
    return {
        "type": "phase",
        "name": phase.name,
        "setup": phase.setup,
        "stabilize": phase.stabilize,
        "steps": steps,
        "teardown": phase.teardown,
    }


def _step_to_instruction(step: IRStep) -> dict[str, Any]:
    params = {k: v for k, v in step.model_dump().items()
              if k not in ("technique", "tag", "extract", "vendor_flags") and v is not None}
    return {"technique": step.technique, "parameters": params, "tag": step.tag}


def _loop_to_instruction(loop: IRLoop) -> dict[str, Any]:
    steps = []
    for s in loop.steps:
        if isinstance(s, IRStep):
            steps.append(_step_to_instruction(s))
    return {"type": "loop", "count": loop.count, "steps": steps}
