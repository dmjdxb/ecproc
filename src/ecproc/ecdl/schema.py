"""ECDL Pydantic v2 models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ECDLMaterial(BaseModel):
    formula_raw: str
    formula_canonical: str | None = None
    composition: dict[str, float] | None = None
    morphology: str | None = None
    support: str | None = None
    synthesis_method: str | None = None
    particle_size_nm: float | None = None
    additional: dict[str, Any] | None = None


class ECDLElectrolyte(BaseModel):
    type: str | None = None
    formula: str | None = None
    concentration_M: float | None = None


class ECDLProtocol(BaseModel):
    name: str
    version: str
    standard_reference: str | None = None
    electrolyte: ECDLElectrolyte | None = None
    ph: float | None = None
    regime: str | None = None
    temperature_C: float | None = None
    potential: dict[str, Any] | None = None
    current_density_mA_cm2: float | None = None
    test_format: str | None = None
    rotation_rpm: int | None = None
    duration_hours: float | None = None
    cycle_count: int | None = None
    additional: dict[str, Any] | None = None


class ECDLObservation(BaseModel):
    tag: str
    metric_type: str
    value: float
    unit: str | None = None
    cycle: int | None = None
    timestamp: str | None = None
    conditions: dict[str, Any] | None = None
    data_file: str | None = None


class ECDLHazardComponents(BaseModel):
    H_temperature: float | None = None
    H_ph: float | None = None
    H_potential: float | None = None
    H_current: float | None = None
    H_format: float | None = None


class ECDLHazard(BaseModel):
    severity_index: float | None = None
    hazard_raw: float | None = None
    components: ECDLHazardComponents | None = None
    uncertainty_factor: float | None = None
    potential_was_soft_capped: bool | None = None


class ECDLNormalization(BaseModel):
    tau_normalized: float | None = None
    reference_hazard: float = 1.0
    was_clipped: bool | None = None
    confidence_tier: str | None = None
    recommendation: str | None = None


class ECDLCompleteness(BaseModel):
    physics_completeness: float | None = None
    reporting_completeness: float | None = None
    missing_fields: list[str] | None = None


class ECDLExposureAdequacy(BaseModel):
    score: float | None = None
    tier: str | None = None


class ECDLFaradayProvenance(BaseModel):
    procedure_name: str
    procedure_version: str
    ir_hash: str
    source_file: str | None = None


class ECDLExecutionProvenance(BaseModel):
    started: str
    completed: str
    hardware: str
    hardware_serial: str | None = None
    operator: str | None = None
    lab_id: str | None = None


class ECDLProvenance(BaseModel):
    faraday: ECDLFaradayProvenance | None = None
    execution: ECDLExecutionProvenance | None = None
    doi: str | None = None
    title: str | None = None
    authors: list[str] | None = None
    journal: str | None = None
    year: int | None = None
    extraction_date: str | None = None
    verification_status: str | None = None


class ECDLDocument(BaseModel):
    ecdl_version: str = "1.0.0"
    id: str | None = None
    material: ECDLMaterial
    protocol: ECDLProtocol
    observation: ECDLObservation | None = None
    observations: list[ECDLObservation] | None = None
    hazard: ECDLHazard | None = None
    completeness: ECDLCompleteness | None = None
    exposure_adequacy: ECDLExposureAdequacy | None = None
    normalization: ECDLNormalization | None = None
    provenance: ECDLProvenance | None = None
    metadata: dict[str, Any] | None = None
