"""ECDL generator - creates ECDL records from IR + execution results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ecproc.ecdl.schema import (
    ECDLDocument,
    ECDLExecutionProvenance,
    ECDLFaradayProvenance,
    ECDLMaterial,
    ECDLObservation,
    ECDLProtocol,
    ECDLProvenance,
)
from ecproc.ir.hash import compute_ir_hash
from ecproc.ir.schema import FaradayIR, IRElectrolyte

if TYPE_CHECKING:
    from ecproc.targets.base import ExecutionResult


def generate_ecdl(ir: FaradayIR, results: ExecutionResult) -> ECDLDocument:
    """Generate ECDL document from IR and execution results."""
    material = ECDLMaterial(formula_raw="unknown")
    if ir.system.working:
        material = ECDLMaterial(formula_raw=ir.system.working.material)

    protocol = ECDLProtocol(
        name=ir.metadata.protocol,
        version=ir.metadata.version,
    )
    if isinstance(ir.system.electrolyte, IRElectrolyte):
        from ecproc.ecdl.schema import ECDLElectrolyte
        protocol.electrolyte = ECDLElectrolyte(
            type=ir.system.electrolyte.solute,
            concentration_M=ir.system.electrolyte.concentration_mol_m3 / 1e3,
        )

    observations = []
    for obs in results.observations:
        tag = obs.get("tag", "")
        data = obs.get("data", {})
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, (int, float)):
                    observations.append(ECDLObservation(
                        tag=tag,
                        metric_type=key,
                        value=float(val),
                    ))

    ir_data = ir.model_dump()
    ir_hash = compute_ir_hash(ir_data)

    provenance = ECDLProvenance(
        faraday=ECDLFaradayProvenance(
            procedure_name=ir.metadata.protocol,
            procedure_version=ir.metadata.version,
            ir_hash=ir_hash,
            source_file=ir.provenance.source_file,
        ),
        execution=ECDLExecutionProvenance(
            started=results.started,
            completed=results.completed,
            hardware=results.hardware,
        ),
    )

    return ECDLDocument(
        material=material,
        protocol=protocol,
        observations=observations,
        provenance=provenance,
    )
