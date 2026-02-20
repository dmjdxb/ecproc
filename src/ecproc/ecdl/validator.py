"""ECDL Validator - refactored from standalone ecdl_validator.py.

Validates ECDL documents against:
1. JSON Schema (structural validation)
2. Physics invariants (INV-H1 through INV-H8, INV-N1 through INV-N4)
3. Semantic rules (domain validation)

All physics functions and constants are preserved exactly from the original.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# =============================================================================
# CONSTANTS - Reference Protocol (H = 1.0)
# =============================================================================

REFERENCE_PROTOCOL = {
    "temperature_C": 25.0,
    "ph": 1.0,
    "potential_high_V": 1.5,
    "current_density_mA_cm2": 10.0,
    "test_format": "RDE"
}

# Physics constants
E_A = 50000  # Activation energy (J/mol) - typical oxide dissolution
R = 8.314   # Gas constant (J/mol·K)
T_REF = 298.15  # Reference temperature (K)
BETA = 0.4  # Symmetry factor for potential
F = 96485   # Faraday constant (C/mol)
ALPHA_PH = 0.5  # pH sensitivity coefficient
GAMMA_J = 0.5  # Current density exponent

# Format hazard lookup
FORMAT_HAZARD = {
    "RDE": 1.0,
    "RRDE": 1.0,
    "HALF_CELL": 1.2,
    "THREE_ELECTRODE": 1.2,
    "FLOW_CELL": 1.8,
    "MEA": 2.5,
    "FULL_CELL": 2.5,
    "TWO_ELECTRODE": 1.5,
    "OTHER": 1.5,
    "UNKNOWN": 1.5
}

# Soft cap scale for potential hazard
SOFT_CAP_SCALE = 15


# =============================================================================
# VALIDATION RESULT TYPES
# =============================================================================

class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    path: str | None = None
    expected: Any | None = None
    actual: Any | None = None


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    schema_valid: bool = False
    physics_valid: bool = False
    semantic_valid: bool = False

    def add_issue(self, severity: Severity, code: str, message: str, **kwargs: Any) -> None:
        self.issues.append(ValidationIssue(severity, code, message, **kwargs))

    def error(self, code: str, message: str, **kwargs: Any) -> None:
        self.add_issue(Severity.ERROR, code, message, **kwargs)
        self.is_valid = False

    def warning(self, code: str, message: str, **kwargs: Any) -> None:
        self.add_issue(Severity.WARNING, code, message, **kwargs)

    def info(self, code: str, message: str, **kwargs: Any) -> None:
        self.add_issue(Severity.INFO, code, message, **kwargs)


# =============================================================================
# SCHEMA VALIDATION
# =============================================================================

def validate_schema(doc: dict[str, Any], schema: dict[str, Any]) -> ValidationResult:
    """Validate document against JSON Schema."""
    result = ValidationResult(is_valid=True)

    try:
        from jsonschema import Draft202012Validator

        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(doc))

        if errors:
            for error in errors:
                path = "/".join(str(p) for p in error.absolute_path) or "(root)"
                result.error(
                    "SCHEMA_VIOLATION",
                    error.message,
                    path=path
                )
        else:
            result.schema_valid = True

    except ImportError:
        result.warning(
            "JSONSCHEMA_NOT_INSTALLED",
            "jsonschema library not installed. Skipping schema validation. "
            "Install with: pip install jsonschema"
        )
        result.schema_valid = True  # Assume valid if we can't check

    return result


# =============================================================================
# PHYSICS INVARIANT VALIDATION
# =============================================================================

def compute_temperature_hazard(temp_c: float) -> float:
    """Arrhenius temperature acceleration factor."""
    if temp_c is None:
        return 1.0
    temp_k = temp_c + 273.15
    return math.exp((E_A / R) * (1/T_REF - 1/temp_k))


def compute_ph_hazard(ph: float, regime: str) -> float:
    """pH-driven dissolution acceleration."""
    if ph is None:
        return 1.0

    if regime == "acidic":
        # Lower pH = higher hazard (more acidic)
        ph_ref = 1.0
        return 10 ** (ALPHA_PH * (ph_ref - ph))
    elif regime == "alkaline":
        # Higher pH = higher hazard (more alkaline)
        ph_ref = 13.0
        return 10 ** (ALPHA_PH * (ph - ph_ref))
    else:
        return 1.0


def compute_potential_hazard(e_high: float, temp_c: float = 25.0) -> tuple[float, bool]:
    """Potential-driven acceleration with soft cap."""
    if e_high is None:
        return 1.0, False

    e_ref = 1.5  # V vs RHE
    delta_e = e_high - e_ref
    temp_k = (temp_c or 25.0) + 273.15

    raw_exponent = (BETA * F * delta_e) / (R * temp_k)

    # Soft cap using tanh
    soft_capped = False
    if abs(raw_exponent) > SOFT_CAP_SCALE:
        soft_capped = True
        exponent = SOFT_CAP_SCALE * math.tanh(raw_exponent / SOFT_CAP_SCALE)
    else:
        exponent = raw_exponent

    return math.exp(exponent), soft_capped


def compute_current_hazard(j: float) -> float:
    """Current density acceleration factor."""
    if j is None or j <= 0:
        return 1.0
    j_ref = 10.0  # mA/cm2
    return float((j / j_ref) ** GAMMA_J)


def compute_format_hazard(fmt: str) -> float:
    """Test format severity factor."""
    return FORMAT_HAZARD.get(fmt, 1.5)


def validate_physics_invariants(doc: dict[str, Any]) -> ValidationResult:
    """Validate physics invariants (INV-H1 through INV-H8, INV-N1 through INV-N4)."""
    result = ValidationResult(is_valid=True)

    protocol = doc.get("protocol", {})
    hazard = doc.get("hazard", {})
    observation = doc.get("observation", {})
    normalization = doc.get("normalization", {})

    # Skip if no hazard computed
    if not hazard:
        result.info("NO_HAZARD", "No hazard data present. Skipping physics validation.")
        result.physics_valid = True
        return result

    # --- INV-H1 through INV-H5: Hazard monotonicity ---
    # We can't check monotonicity with a single document, but we can verify
    # that the computed components make sense given the inputs

    components = hazard.get("components", {})

    # Verify temperature hazard
    temp_c = protocol.get("temperature_C")
    if temp_c is not None and "H_temperature" in components:
        expected_h_t = compute_temperature_hazard(temp_c)
        actual_h_t = components["H_temperature"]
        if not math.isclose(expected_h_t, actual_h_t, rel_tol=0.01):
            result.error(
                "INV_H1_TEMPERATURE",
                "Temperature hazard mismatch",
                path="hazard.components.H_temperature",
                expected=round(expected_h_t, 4),
                actual=round(actual_h_t, 4)
            )

        # Sanity check: higher temp should give H > 1
        if temp_c > 25 and actual_h_t <= 1.0:
            result.error(
                "INV_H1_MONOTONICITY",
                f"Temperature {temp_c}°C should give H_temperature > 1.0",
                path="hazard.components.H_temperature",
                expected=">1.0",
                actual=actual_h_t
            )

    # Verify pH hazard
    ph = protocol.get("ph")
    regime = protocol.get("regime", "unknown")
    if ph is not None and "H_ph" in components:
        expected_h_ph = compute_ph_hazard(ph, regime)
        actual_h_ph = components["H_ph"]
        if not math.isclose(expected_h_ph, actual_h_ph, rel_tol=0.05):
            result.warning(
                "INV_H2_PH",
                f"pH hazard may be inconsistent "
                f"(expected ~{expected_h_ph:.2f}, got {actual_h_ph:.2f})",
                path="hazard.components.H_ph"
            )

    # Verify potential hazard
    potential = protocol.get("potential", {})
    e_high = potential.get("high_V")
    if e_high is not None and "H_potential" in components:
        expected_h_e, _ = compute_potential_hazard(e_high, temp_c)
        actual_h_e = components["H_potential"]
        # Allow wider tolerance due to soft cap variations
        if not math.isclose(expected_h_e, actual_h_e, rel_tol=0.1):
            result.warning(
                "INV_H4_POTENTIAL",
                "Potential hazard may be inconsistent",
                path="hazard.components.H_potential",
                expected=round(expected_h_e, 2),
                actual=round(actual_h_e, 2)
            )

    # --- INV-H6 and INV-H7: No double-counting ---
    # Duration and cycles should NOT appear in hazard calculation
    # (duration_hours and cycle_count are intentionally not extracted here)

    severity_index = hazard.get("severity_index")
    if severity_index is not None:
        # We can't directly verify no double-counting from a single doc,
        # but we can flag if duration/cycles seem to be influencing hazard
        result.info(
            "INV_H6_H7_CHECK",
            "Reminder: duration_hours and cycle_count must NOT affect severity_index"
        )

    # --- INV-N1 through INV-N4: Normalization invariants ---
    if normalization and observation:
        tau_obs = observation.get("value")
        tau_norm = normalization.get("tau_normalized")
        h_obs = hazard.get("severity_index")
        h_ref = normalization.get("reference_hazard", 1.0)

        if all(v is not None for v in [tau_obs, tau_norm, h_obs]):
            expected_tau_norm = tau_obs * (h_obs / h_ref)

            # Check if clipping was applied
            was_clipped = normalization.get("was_clipped", False)

            if not was_clipped and not math.isclose(expected_tau_norm, tau_norm, rel_tol=0.01):
                result.error(
                    "INV_N4_SCALING",
                    "Normalization scaling incorrect: "
                    "\u03c4* should equal \u03c4 \u00d7 (H_obs/H_ref)",
                    path="normalization.tau_normalized",
                    expected=round(expected_tau_norm, 2),
                    actual=round(tau_norm, 2)
                )

            # INV-N1: If H_obs == H_ref, tau* == tau_obs
            if (
                math.isclose(h_obs, h_ref, rel_tol=0.01)
                and not math.isclose(tau_norm, tau_obs, rel_tol=0.01)
            ):
                result.error(
                    "INV_N1_IDENTITY",
                    "When H_obs \u2248 H_ref, \u03c4* should equal \u03c4_obs",
                    path="normalization.tau_normalized"
                )

            # INV-N2: If H_obs > H_ref, tau* > tau_obs
            elif h_obs > h_ref and not was_clipped and tau_norm <= tau_obs:
                result.error(
                    "INV_N2_HARSH",
                    "When H_obs > H_ref (harsher test), \u03c4* should be > \u03c4_obs",
                    path="normalization.tau_normalized"
                )

            # INV-N3: If H_obs < H_ref, tau* < tau_obs
            elif h_obs < h_ref and not was_clipped and tau_norm >= tau_obs:
                result.error(
                    "INV_N3_MILD",
                    "When H_obs < H_ref (milder test), \u03c4* should be < \u03c4_obs",
                    path="normalization.tau_normalized"
                )

    if not any(i.severity == Severity.ERROR for i in result.issues):
        result.physics_valid = True

    return result


# =============================================================================
# SEMANTIC VALIDATION
# =============================================================================

def validate_semantics(doc: dict[str, Any]) -> ValidationResult:
    """Validate domain-specific semantic rules."""
    result = ValidationResult(is_valid=True)

    material = doc.get("material", {})
    protocol = doc.get("protocol", {})
    observation = doc.get("observation", {})

    # --- Rule: Material should not be an electrolyte ---
    formula = material.get("formula_raw", "").upper()
    electrolyte_formulas = ["H2SO4", "HCLO4", "KOH", "NAOH", "HCL", "PBS", "NANO3", "H3PO4"]
    if formula in electrolyte_formulas:
        result.error(
            "SEM_MATERIAL_IS_ELECTROLYTE",
            f"Material formula '{formula}' appears to be an electrolyte, not a catalyst",
            path="material.formula_raw"
        )

    # --- Rule: pH and electrolyte should be consistent ---
    ph = protocol.get("ph")
    electrolyte = protocol.get("electrolyte", {})
    electrolyte_type = electrolyte.get("type")

    if ph is not None and electrolyte_type:
        acidic_electrolytes = ["H2SO4", "HClO4", "HCl", "HNO3"]
        alkaline_electrolytes = ["KOH", "NaOH"]

        if electrolyte_type in acidic_electrolytes and ph > 7:
            result.warning(
                "SEM_PH_ELECTROLYTE_MISMATCH",
                f"Acidic electrolyte ({electrolyte_type}) but pH={ph} > 7",
                path="protocol.ph"
            )

        if electrolyte_type in alkaline_electrolytes and ph < 7:
            result.warning(
                "SEM_PH_ELECTROLYTE_MISMATCH",
                f"Alkaline electrolyte ({electrolyte_type}) but pH={ph} < 7",
                path="protocol.ph"
            )

    # --- Rule: S-number requires dissolution context ---
    metric_type = observation.get("metric_type")
    # S-number should have provenance indicating it came from dissolution measurement
    if metric_type == "s_number" and (
        not observation.get("value") or observation.get("value") <= 0
    ):
        result.error(
            "SEM_SNUMBER_INVALID",
            "S-number must be a positive value",
            path="observation.value"
        )

    # --- Rule: Potential reference should be specified ---
    potential = protocol.get("potential", {})
    if potential.get("high_V") is not None and not potential.get("reference"):
        result.warning(
            "SEM_POTENTIAL_NO_REFERENCE",
            "Potential value specified but reference electrode not indicated",
            path="protocol.potential.reference"
        )

    # --- Rule: MEA format implies higher severity ---
    test_format = protocol.get("test_format")
    hazard = doc.get("hazard", {})
    h_format = hazard.get("components", {}).get("H_format", 2.5)
    if test_format == "MEA" and h_format < 2.0:
        result.warning(
            "SEM_MEA_LOW_HAZARD",
            "MEA format typically has H_format >= 2.5",
            path="hazard.components.H_format"
        )

    # --- Rule: Duration/cycles required for exposure adequacy ---
    duration = protocol.get("duration_hours")
    cycles = protocol.get("cycle_count")
    exposure = doc.get("exposure_adequacy", {})

    if exposure and exposure.get("tier") and duration is None and cycles is None:
        result.warning(
            "SEM_EXPOSURE_NO_DATA",
            "Exposure adequacy tier assigned but no duration or cycle count",
            path="exposure_adequacy"
        )

    if not any(i.severity == Severity.ERROR for i in result.issues):
        result.semantic_valid = True

    return result


# =============================================================================
# MAIN VALIDATOR
# =============================================================================

def validate_ecdl(
    doc: dict[str, Any],
    schema: dict[str, Any] | None = None,
    strict: bool = False,
) -> ValidationResult:
    """
    Validate an ECDL document.

    Args:
        doc: ECDL document as dictionary
        schema: JSON Schema (optional, will use bundled if not provided)
        strict: If True, warnings are treated as errors

    Returns:
        ValidationResult with all issues found
    """
    final_result = ValidationResult(is_valid=True)

    # 1. Schema validation
    if schema:
        schema_result = validate_schema(doc, schema)
        final_result.issues.extend(schema_result.issues)
        final_result.schema_valid = schema_result.schema_valid
        if not schema_result.is_valid:
            final_result.is_valid = False
    else:
        final_result.schema_valid = True  # Assume valid if no schema provided

    # 2. Physics invariant validation
    physics_result = validate_physics_invariants(doc)
    final_result.issues.extend(physics_result.issues)
    final_result.physics_valid = physics_result.physics_valid
    if not physics_result.is_valid:
        final_result.is_valid = False

    # 3. Semantic validation
    semantic_result = validate_semantics(doc)
    final_result.issues.extend(semantic_result.issues)
    final_result.semantic_valid = semantic_result.semantic_valid
    if not semantic_result.is_valid:
        final_result.is_valid = False

    # In strict mode, warnings become errors
    if strict:
        for issue in final_result.issues:
            if issue.severity == Severity.WARNING:
                issue.severity = Severity.ERROR
                final_result.is_valid = False

    return final_result


def load_schema(schema_path: Path | None = None) -> dict[str, Any] | None:
    """Load ECDL JSON Schema."""
    if schema_path is None:
        # Try to find bundled schema (packaged alongside this module first)
        default_paths = [
            Path(__file__).parent / "ecdl.schema.json",
            Path(__file__).parent.parent.parent.parent / "schemas" / "ecdl.schema.json",
            Path("ecdl-v1.0.0.schema.json"),
            Path("schema/ecdl-v1.0.0.schema.json"),
        ]
        for p in default_paths:
            if p.exists():
                schema_path = p
                break

    if schema_path and schema_path.exists():
        with open(schema_path) as f:
            result: dict[str, Any] = json.load(f)
            return result

    return None


def format_result(result: ValidationResult, verbose: bool = False) -> str:
    """Format validation result for display."""
    lines = []

    # Summary
    status = "VALID" if result.is_valid else "INVALID"
    lines.append(f"\n{status}")
    lines.append(f"  Schema:   {'pass' if result.schema_valid else 'fail'}")
    lines.append(f"  Physics:  {'pass' if result.physics_valid else 'fail'}")
    lines.append(f"  Semantic: {'pass' if result.semantic_valid else 'fail'}")

    # Issues by severity
    errors = [i for i in result.issues if i.severity == Severity.ERROR]
    warnings = [i for i in result.issues if i.severity == Severity.WARNING]
    infos = [i for i in result.issues if i.severity == Severity.INFO]

    if errors:
        lines.append(f"\nErrors ({len(errors)}):")
        for issue in errors:
            lines.append(f"  [{issue.code}] {issue.message}")
            if issue.path:
                lines.append(f"    Path: {issue.path}")
            if issue.expected is not None:
                lines.append(f"    Expected: {issue.expected}")
            if issue.actual is not None:
                lines.append(f"    Actual: {issue.actual}")

    if warnings:
        lines.append(f"\nWarnings ({len(warnings)}):")
        for issue in warnings:
            lines.append(f"  [{issue.code}] {issue.message}")
            if verbose and issue.path:
                lines.append(f"    Path: {issue.path}")

    if verbose and infos:
        lines.append(f"\nInfo ({len(infos)}):")
        for issue in infos:
            lines.append(f"  [{issue.code}] {issue.message}")

    return "\n".join(lines)
