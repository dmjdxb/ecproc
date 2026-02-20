"""Faraday IR Pydantic v2 models.

All values use SI base units internally:
    Potential = V, Current = A, Duration = s, Frequency = Hz,
    Area = m^2, Loading = kg/m^2, Concentration = mol/m^3
    Temperature = C (electrochemistry convention exception)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# --- Leaf models (no forward references) ---


class IRWorkingElectrode(BaseModel):
    material: str
    area_m2: float | None = None
    loading_kg_m2: float | None = None
    additional: dict[str, Any] | None = None


class IRElectrolyte(BaseModel):
    solute: str
    concentration_mol_m3: float
    additional: dict[str, Any] | None = None


class IRSystem(BaseModel):
    electrodes: int
    reference: str
    working: IRWorkingElectrode | None = None
    electrolyte: str | IRElectrolyte | None = None
    counter: str | None = None


class IRStep(BaseModel, extra="allow"):
    """A single electrochemical step. Technique-specific fields via extra='allow'."""
    technique: str
    tag: str | None = None
    extract: str | dict[str, str] | None = None
    vendor_flags: dict[str, dict[str, Any]] | None = None


class IRTrigger(BaseModel):
    type: str
    value: int | float | str
    unit: str | None = None


class IRMetadata(BaseModel):
    protocol: str
    version: str
    created: datetime
    ecproc_version: str
    source_hash: str
    author: str | None = None


class IRThermalRunaway(BaseModel):
    max_dT_dt_K_s: float  # K/s (converted from C/min)
    action: str


class IRReferenceMonitor(BaseModel):
    max_Ru_change_factor: float | None = None
    max_ocp_drift_V_s: float | None = None
    action: str = "cell_off"


class IRVariables(BaseModel):
    """Extracted variable values (e.g., Ru from EIS)."""
    extractions: dict[str, str] = Field(default_factory=dict)


class IROutput(BaseModel):
    ecdl: dict[str, Any] | None = None


class IRProvenance(BaseModel):
    source_file: str | None = None
    source_hash: str
    parser_version: str


class IRStateRecovery(BaseModel):
    after_pause: list[IRStep] | None = None
    after_checkpoint: list[IRStep] | None = None
    after_error: list[IRStep | str] | None = None


# --- Models with forward references (use string annotations) ---


class IRCheckpoint(BaseModel):
    triggers: list[IRTrigger]
    logic: str = "any"
    reset: str = "independent"
    do: list[IRStep | IRPhase] = Field(default_factory=list)


class IRLoop(BaseModel):
    count: int | str
    steps: list[IRStep | IRLoop]
    checkpoint: IRCheckpoint | None = None
    stop_if: str | None = None


class IRSafety(BaseModel):
    max_current_A: float | None = None
    voltage_window_V: tuple[float, float] | None = None
    temperature_limits_C: tuple[float, float] | None = None
    stop_conditions: list[str] | None = None
    thermal_runaway: IRThermalRunaway | None = None
    reference_electrode_monitor: IRReferenceMonitor | None = None


class IRPhase(BaseModel):
    name: str
    setup: dict[str, Any] | None = None
    stabilize: list[str] | None = None
    steps: list[IRStep | IRLoop]
    teardown: dict[str, Any] | None = None


class FaradayIR(BaseModel):
    faraday_version: str = "1.0"
    metadata: IRMetadata
    system: IRSystem
    procedure: list[IRPhase]
    safety: IRSafety | None = None
    state_recovery: IRStateRecovery | None = None
    variables: IRVariables | None = None
    output: IROutput | None = None
    provenance: IRProvenance


# Rebuild models with forward references
IRLoop.model_rebuild()
IRCheckpoint.model_rebuild()
IRPhase.model_rebuild()
FaradayIR.model_rebuild()
