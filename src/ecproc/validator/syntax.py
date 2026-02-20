"""L1: Syntax validation - structural checks on Faraday IR."""

from __future__ import annotations

from ecproc.ir.schema import FaradayIR, IRLoop, IRPhase, IRStep
from ecproc.validator.errors import ValidationResult

VALID_TECHNIQUES = frozenset({
    "cv", "lsv", "eis", "ocp", "hold", "galvanostatic",
    "dpv", "swv", "gcd", "cc", "stripping", "purge",
})


def validate_syntax(ir: FaradayIR) -> ValidationResult:
    """Run L1 syntax validation on a FaradayIR."""
    result = ValidationResult()

    # Metadata checks
    if not ir.metadata.protocol:
        result.add_error("L1", "SYN001", "Missing metadata.protocol", path="metadata.protocol")
    if not ir.metadata.version:
        result.add_error("L1", "SYN002", "Missing metadata.version", path="metadata.version")

    # System checks
    if ir.system.electrodes not in (2, 3):
        result.add_error(
            "L1", "SYN003",
            f"system.electrodes must be 2 or 3, got {ir.system.electrodes}",
            path="system.electrodes",
        )
    if not ir.system.reference:
        result.add_error("L1", "SYN004", "Missing system.reference", path="system.reference")

    # Procedure checks
    if not ir.procedure:
        result.add_error(
            "L1", "SYN005", "Procedure must have at least one phase", path="procedure"
        )

    for i, phase in enumerate(ir.procedure):
        _validate_phase(phase, f"procedure[{i}]", result)

    return result


def _validate_phase(phase: IRPhase, path: str, result: ValidationResult) -> None:
    if not phase.name:
        result.add_error("L1", "SYN006", "Phase must have a name", path=f"{path}.name")
    if not phase.steps:
        result.add_error("L1", "SYN007", "Phase must have at least one step", path=f"{path}.steps")
    for j, step in enumerate(phase.steps):
        if isinstance(step, IRStep):
            _validate_step(step, f"{path}.steps[{j}]", result)
        elif isinstance(step, IRLoop):
            _validate_loop(step, f"{path}.steps[{j}]", result)


def _validate_step(step: IRStep, path: str, result: ValidationResult) -> None:
    if not step.technique:
        result.add_error("L1", "SYN008", "Step must have a technique", path=f"{path}.technique")
    elif step.technique not in VALID_TECHNIQUES:
        result.add_error(
            "L1", "SYN009",
            f"Unknown technique: '{step.technique}'",
            path=f"{path}.technique",
        )


def _validate_loop(loop: IRLoop, path: str, result: ValidationResult) -> None:
    if not loop.steps:
        result.add_error("L1", "SYN010", "Loop must have at least one step", path=f"{path}.steps")
    for j, step in enumerate(loop.steps):
        if isinstance(step, IRStep):
            _validate_step(step, f"{path}.steps[{j}]", result)
        elif isinstance(step, IRLoop):
            _validate_loop(step, f"{path}.steps[{j}]", result)
