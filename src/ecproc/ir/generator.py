"""AST to Faraday IR transformation.

Unit normalization happens at this boundary:
    mV/s -> V/s, mA -> A, cm2 -> m2, ug/cm2 -> kg/m2,
    M -> mol/m3, kHz/MHz -> Hz, min/h -> s
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ecproc._version import __version__
from ecproc.ir.hash import compute_source_hash
from ecproc.ir.schema import (
    FaradayIR,
    IRCheckpoint,
    IRElectrolyte,
    IRLoop,
    IRMetadata,
    IROutput,
    IRPhase,
    IRProvenance,
    IRReferenceMonitor,
    IRSafety,
    IRStateRecovery,
    IRStep,
    IRSystem,
    IRThermalRunaway,
    IRTrigger,
    IRVariables,
    IRWorkingElectrode,
)
from ecproc.parser.ast import (
    CheckpointAST,
    ElectrolyteAST,
    LoopAST,
    PhaseAST,
    ProcedureAST,
    SafetyAST,
    StepAST,
    TriggerAST,
)
from ecproc.utils.units import normalize_to_si, parse_value_unit


def generate_ir(ast: ProcedureAST) -> FaradayIR:
    """Transform a ProcedureAST into a FaradayIR.

    Performs unit normalization to SI base units at this boundary.
    """
    source_hash = compute_source_hash(ast)

    metadata = IRMetadata(
        protocol=ast.metadata.protocol,
        version=ast.metadata.version,
        created=datetime.now(timezone.utc),
        ecproc_version=__version__,
        source_hash=source_hash,
        author=ast.metadata.author,
    )

    system = _convert_system(ast.system)
    phases = [_convert_phase(p) for p in ast.procedure]
    safety = _convert_safety(ast.safety) if ast.safety else None
    state_recovery = _convert_state_recovery(ast.state_recovery) if ast.state_recovery else None
    variables = _collect_variables(ast)
    output = IROutput(ecdl=ast.output.ecdl) if ast.output else None

    provenance = IRProvenance(
        source_file=str(ast.source_file) if ast.source_file else None,
        source_hash=source_hash,
        parser_version=__version__,
    )

    return FaradayIR(
        metadata=metadata,
        system=system,
        procedure=phases,
        safety=safety,
        state_recovery=state_recovery,
        variables=variables,
        output=output,
        provenance=provenance,
    )


def _convert_system(sys: Any) -> IRSystem:
    working = None
    if sys.working:
        w = sys.working
        area_m2 = w.area_cm2 * 1e-4 if w.area_cm2 is not None else None
        loading_kg_m2 = w.loading_ug_cm2 * 1e-5 if w.loading_ug_cm2 is not None else None
        working = IRWorkingElectrode(
            material=w.material,
            area_m2=area_m2,
            loading_kg_m2=loading_kg_m2,
            additional=w.additional,
        )

    electrolyte: str | IRElectrolyte | None = None
    if sys.electrolyte is not None:
        if isinstance(sys.electrolyte, str):
            electrolyte = sys.electrolyte
        elif isinstance(sys.electrolyte, ElectrolyteAST):
            electrolyte = IRElectrolyte(
                solute=sys.electrolyte.solute,
                concentration_mol_m3=sys.electrolyte.concentration_M * 1e3,
                additional=sys.electrolyte.additional,
            )

    return IRSystem(
        electrodes=sys.electrodes,
        reference=sys.reference,
        working=working,
        electrolyte=electrolyte,
        counter=sys.counter,
    )


def _normalize_step_params(params: dict[str, Any]) -> dict[str, Any]:
    """Normalize step parameters from human units to SI."""
    result: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, str):
            try:
                v, u = parse_value_unit(value)
                si_v, si_u = normalize_to_si(v, u)
                result[key] = si_v
            except ValueError:
                result[key] = value
        else:
            result[key] = value
    return result


def _convert_step(step: StepAST) -> IRStep:
    params = _normalize_step_params(step.parameters)
    # Remove keys that are set explicitly to avoid duplicate keyword args
    reserved = {"technique", "tag", "extract", "vendor_flags"}
    extra = {k: v for k, v in params.items() if k not in reserved}
    return IRStep(
        technique=step.technique,
        tag=step.tag,
        extract=step.extract,
        vendor_flags=step.vendor_flags,
        **extra,
    )


def _convert_trigger(t: TriggerAST) -> IRTrigger:
    return IRTrigger(type=t.type, value=t.value, unit=t.unit)


def _convert_checkpoint(cp: CheckpointAST) -> IRCheckpoint:
    do_items: list[IRStep | IRPhase] = []
    for item in cp.do:
        if isinstance(item, StepAST):
            do_items.append(_convert_step(item))
        elif isinstance(item, PhaseAST):
            do_items.append(_convert_phase(item))
    return IRCheckpoint(
        triggers=[_convert_trigger(t) for t in cp.triggers],
        logic=cp.logic,
        reset=cp.reset,
        do=do_items,
    )


def _convert_loop(loop: LoopAST) -> IRLoop:
    steps: list[IRStep | IRLoop] = []
    for s in loop.steps:
        if isinstance(s, StepAST):
            steps.append(_convert_step(s))
        elif isinstance(s, LoopAST):
            steps.append(_convert_loop(s))
    return IRLoop(
        count=loop.count,
        steps=steps,
        checkpoint=_convert_checkpoint(loop.checkpoint) if loop.checkpoint else None,
        stop_if=loop.stop_if,
    )


def _convert_phase(phase: PhaseAST) -> IRPhase:
    steps: list[IRStep | IRLoop] = []
    for s in phase.steps:
        if isinstance(s, StepAST):
            steps.append(_convert_step(s))
        elif isinstance(s, LoopAST):
            steps.append(_convert_loop(s))
    return IRPhase(
        name=phase.name,
        setup=phase.setup,
        stabilize=phase.stabilize,
        steps=steps,
        teardown=phase.teardown,
    )


def _convert_safety(safety: SafetyAST) -> IRSafety:
    max_current_A = None
    if safety.max_current:
        try:
            v, u = parse_value_unit(safety.max_current)
            max_current_A, _ = normalize_to_si(v, u)
        except ValueError:
            pass

    voltage_window_V = None
    if safety.voltage_window and len(safety.voltage_window) == 2:
        try:
            v1, u1 = parse_value_unit(safety.voltage_window[0])
            v2, u2 = parse_value_unit(safety.voltage_window[1])
            sv1, _ = normalize_to_si(v1, u1)
            sv2, _ = normalize_to_si(v2, u2)
            voltage_window_V = (sv1, sv2)
        except ValueError:
            pass

    temp_limits_C = None
    if safety.temperature_limits and len(safety.temperature_limits) == 2:
        try:
            t1, _ = parse_value_unit(safety.temperature_limits[0])
            t2, _ = parse_value_unit(safety.temperature_limits[1])
            temp_limits_C = (t1, t2)
        except ValueError:
            pass

    thermal = None
    if safety.thermal_runaway:
        # Convert C/min to K/s: divide by 60
        thermal = IRThermalRunaway(
            max_dT_dt_K_s=safety.thermal_runaway.max_dT_dt / 60.0,
            action=safety.thermal_runaway.action,
        )

    ref_monitor = None
    if safety.reference_electrode_monitor:
        rm = safety.reference_electrode_monitor
        factor = None
        if rm.max_Ru_change:
            factor = float(rm.max_Ru_change.replace("x", "").strip())
        drift = None
        if rm.max_ocp_drift:
            try:
                v, u = parse_value_unit(rm.max_ocp_drift)
                drift, _ = normalize_to_si(v, u)
            except ValueError:
                pass
        ref_monitor = IRReferenceMonitor(
            max_Ru_change_factor=factor,
            max_ocp_drift_V_s=drift,
            action=rm.action,
        )

    return IRSafety(
        max_current_A=max_current_A,
        voltage_window_V=voltage_window_V,
        temperature_limits_C=temp_limits_C,
        stop_conditions=safety.stop_if,
        thermal_runaway=thermal,
        reference_electrode_monitor=ref_monitor,
    )


def _convert_state_recovery(sr: Any) -> IRStateRecovery:
    after_pause = [_convert_step(s) for s in sr.after_pause] if sr.after_pause else None
    after_checkpoint = (
        [_convert_step(s) for s in sr.after_checkpoint] if sr.after_checkpoint else None
    )
    after_error: list[IRStep | str] | None = None
    if sr.after_error:
        after_error = []
        for item in sr.after_error:
            if isinstance(item, StepAST):
                after_error.append(_convert_step(item))
            else:
                after_error.append(str(item))
    return IRStateRecovery(
        after_pause=after_pause,
        after_checkpoint=after_checkpoint,
        after_error=after_error,
    )


def _collect_variables(ast: ProcedureAST) -> IRVariables | None:
    """Collect all extract fields from steps into IRVariables."""
    extractions: dict[str, str] = {}
    for phase in ast.procedure:
        for step in phase.steps:
            if isinstance(step, StepAST) and step.extract:
                tag = step.tag or step.technique
                if isinstance(step.extract, str):
                    extractions[tag] = step.extract
                elif isinstance(step.extract, dict):
                    for k, v in step.extract.items():
                        extractions[f"{tag}.{k}"] = v
    if extractions:
        return IRVariables(extractions=extractions)
    return None
