"""Internal AST dataclasses for ecproc procedure representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class SourceLocation:
    line: int
    column: int = 0
    file: str | None = None


@dataclass
class TriggerAST:
    type: str  # "every_cycles", "every_time", "when"
    value: int | float | str
    unit: str | None = None
    source_location: SourceLocation | None = None


@dataclass
class StepAST:
    technique: str  # "cv", "lsv", "eis", "purge", etc.
    parameters: dict[str, Any]
    tag: str | None = None
    extract: str | dict[str, str] | None = None
    vendor_flags: dict[str, dict[str, Any]] | None = None
    source_location: SourceLocation | None = None


@dataclass
class CheckpointAST:
    triggers: list[TriggerAST]
    logic: str = "any"  # "any" or "all"
    reset: str = "independent"  # "independent" or "shared"
    do: list[StepAST | PhaseAST] = field(default_factory=list)
    source_location: SourceLocation | None = None


@dataclass
class LoopAST:
    count: int | str  # int or "{variable}"
    steps: list[StepAST | LoopAST]
    checkpoint: CheckpointAST | None = None
    stop_if: str | None = None
    source_location: SourceLocation | None = None


@dataclass
class PhaseAST:
    name: str
    setup: dict[str, Any] | None = None
    stabilize: list[str] | None = None
    steps: list[StepAST | LoopAST] = field(default_factory=list)
    teardown: dict[str, Any] | None = None
    source_location: SourceLocation | None = None


@dataclass
class WorkingElectrodeAST:
    material: str
    area_cm2: float | None = None
    loading_ug_cm2: float | None = None
    additional: dict[str, Any] | None = None


@dataclass
class ElectrolyteAST:
    solute: str
    concentration_M: float
    additional: dict[str, Any] | None = None


@dataclass
class SystemAST:
    electrodes: int  # 2 or 3
    reference: str  # "RHE", "Ag/AgCl", etc.
    working: WorkingElectrodeAST | None = None
    electrolyte: str | ElectrolyteAST | None = None
    counter: str | None = None
    source_location: SourceLocation | None = None


@dataclass
class ThermalRunawayAST:
    max_dT_dt: float  # deg_C/min
    action: str  # "emergency_stop", "cell_off"


@dataclass
class ReferenceMonitorAST:
    max_Ru_change: str | None = None  # e.g., "10x"
    max_ocp_drift: str | None = None  # e.g., "500 mV/s"
    action: str = "cell_off"


@dataclass
class SafetyAST:
    max_current: str | None = None
    voltage_window: list[str] | None = None
    temperature_limits: list[str] | None = None
    stop_if: list[str] | None = None
    thermal_runaway: ThermalRunawayAST | None = None
    reference_electrode_monitor: ReferenceMonitorAST | None = None
    source_location: SourceLocation | None = None


@dataclass
class StateRecoveryAST:
    after_pause: list[StepAST] | None = None
    after_checkpoint: list[StepAST] | None = None
    after_error: list[StepAST | str] | None = None


@dataclass
class MetadataAST:
    protocol: str
    version: str
    author: str | None = None
    electrolyte: str | None = None
    gas: str | None = None
    working_electrode: str | None = None
    reference: str | None = None
    notes: str | None = None
    additional: dict[str, Any] | None = None


@dataclass
class OutputAST:
    ecdl: dict[str, Any] | None = None


@dataclass
class ProcedureAST:
    metadata: MetadataAST
    system: SystemAST
    procedure: list[PhaseAST]  # NOT "phases"
    safety: SafetyAST | None = None
    state_recovery: StateRecoveryAST | None = None
    output: OutputAST | None = None
    source_file: Path | None = None
