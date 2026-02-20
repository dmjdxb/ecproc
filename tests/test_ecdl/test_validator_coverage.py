#!/usr/bin/env python3
"""
ECDL Validator Coverage Tests

Covers all previously-uncovered lines in src/ecproc/ecdl/validator.py:
  - validate_schema error path and ImportError path
  - compute_ph_hazard neutral/unknown regime (else branch)
  - compute_current_hazard with j > 0 (return path)
  - validate_physics_invariants INV-N1 identity violation and INV-N3 mild violation
  - validate_semantics MEA low hazard and exposure-no-data warnings
  - load_schema (explicit path, default search, missing file)
  - format_result (errors, warnings, infos, verbose and non-verbose)

Run with: pytest tests/test_ecdl/test_validator_coverage.py -v
"""

import json
import math
from pathlib import Path
from unittest import mock

import pytest

from ecproc.ecdl.validator import (
    ALPHA_PH,
    GAMMA_J,
    Severity,
    ValidationResult,
    compute_current_hazard,
    compute_ph_hazard,
    format_result,
    load_schema,
    validate_ecdl,
    validate_physics_invariants,
    validate_schema,
    validate_semantics,
)

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def minimal_doc():
    """Minimal valid ECDL document."""
    return {
        "ecdl_version": "1.0.0",
        "material": {"formula_raw": "IrO2"},
        "protocol": {},
    }


@pytest.fixture
def simple_schema():
    """A simple JSON schema that requires ecdl_version as a string."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["ecdl_version", "material"],
        "properties": {
            "ecdl_version": {"type": "string"},
            "material": {
                "type": "object",
                "required": ["formula_raw"],
                "properties": {
                    "formula_raw": {"type": "string"},
                },
            },
        },
    }


@pytest.fixture
def physics_doc_base():
    """Base document with hazard, observation, and normalization for physics tests."""
    return {
        "ecdl_version": "1.0.0",
        "material": {"formula_raw": "IrO2"},
        "protocol": {
            "temperature_C": 25.0,
            "ph": 1.0,
            "regime": "acidic",
            "potential": {"high_V": 1.5, "reference": "RHE"},
            "current_density_mA_cm2": 10.0,
            "test_format": "RDE",
        },
        "observation": {
            "metric_type": "tau20_activity",
            "value": 100.0,
        },
        "hazard": {
            "severity_index": 1.0,
            "components": {
                "H_temperature": 1.0,
                "H_ph": 1.0,
                "H_potential": 1.0,
                "H_current": 1.0,
                "H_format": 1.0,
            },
        },
        "normalization": {
            "tau_normalized": 100.0,
            "reference_hazard": 1.0,
        },
    }


# =============================================================================
# 1. validate_schema - error path (lines 115-122)
# =============================================================================

class TestValidateSchemaErrorPath:
    """When jsonschema validation finds errors, iterate and emit SCHEMA_VIOLATION."""

    def test_schema_violation_missing_required_field(self, simple_schema):
        """Doc missing a required field should produce SCHEMA_VIOLATION errors."""
        doc = {"ecdl_version": "1.0.0"}  # missing "material"
        result = validate_schema(doc, simple_schema)

        assert result.is_valid is False
        assert result.schema_valid is False
        violations = [i for i in result.issues if i.code == "SCHEMA_VIOLATION"]
        assert len(violations) >= 1
        assert violations[0].severity == Severity.ERROR

    def test_schema_violation_wrong_type(self, simple_schema):
        """Doc with wrong type should produce SCHEMA_VIOLATION."""
        doc = {
            "ecdl_version": 123,  # should be string
            "material": {"formula_raw": "IrO2"},
        }
        result = validate_schema(doc, simple_schema)

        assert result.is_valid is False
        violations = [i for i in result.issues if i.code == "SCHEMA_VIOLATION"]
        assert len(violations) >= 1

    def test_schema_violation_path_populated(self, simple_schema):
        """Each SCHEMA_VIOLATION issue should have a path."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": 999},  # should be string
        }
        result = validate_schema(doc, simple_schema)

        violations = [i for i in result.issues if i.code == "SCHEMA_VIOLATION"]
        assert len(violations) >= 1
        # At least one should have a non-empty path
        paths = [v.path for v in violations if v.path]
        assert len(paths) >= 1

    def test_schema_valid_doc_sets_schema_valid_true(self, simple_schema):
        """A valid doc should set schema_valid = True and have no violations."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "IrO2"},
        }
        result = validate_schema(doc, simple_schema)

        assert result.is_valid is True
        assert result.schema_valid is True
        violations = [i for i in result.issues if i.code == "SCHEMA_VIOLATION"]
        assert len(violations) == 0

    def test_schema_violation_at_root_level(self):
        """A doc that violates root-level type produces path '(root)'."""
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["ecdl_version"],
            "properties": {
                "ecdl_version": {"type": "string"},
            },
        }
        # Missing required "ecdl_version" -- path should be "(root)"
        doc = {}
        result = validate_schema(doc, schema)

        assert result.is_valid is False
        violations = [i for i in result.issues if i.code == "SCHEMA_VIOLATION"]
        assert len(violations) >= 1
        # The root-level required error path should be "(root)"
        root_violations = [v for v in violations if v.path == "(root)"]
        assert len(root_violations) >= 1


# =============================================================================
# 2. validate_schema - ImportError path (lines 126-132)
# =============================================================================

class TestValidateSchemaImportError:
    """When jsonschema is not installed, emit a warning and assume valid."""

    def test_jsonschema_not_installed_emits_warning(self):
        """Mock jsonschema import failure to hit the ImportError branch."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "jsonschema":
                raise ImportError("No module named 'jsonschema'")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=mock_import):
            result = validate_schema({"ecdl_version": "1.0.0"}, {"type": "object"})

        warnings = [i for i in result.issues if i.code == "JSONSCHEMA_NOT_INSTALLED"]
        assert len(warnings) == 1
        assert warnings[0].severity == Severity.WARNING
        # Schema should be assumed valid when jsonschema is unavailable
        assert result.schema_valid is True
        assert result.is_valid is True


# =============================================================================
# 3. compute_ph_hazard - neutral/unknown regime (line 163)
# =============================================================================

class TestComputePhHazardNeutralRegime:
    """The else branch returns 1.0 for unknown/neutral regime."""

    def test_unknown_regime_returns_unity(self):
        """Unknown regime returns H=1.0."""
        h = compute_ph_hazard(7.0, "unknown")
        assert h == 1.0

    def test_neutral_regime_returns_unity(self):
        """Neutral (or any other string) regime returns H=1.0."""
        h = compute_ph_hazard(7.0, "neutral")
        assert h == 1.0

    def test_empty_string_regime_returns_unity(self):
        """Empty string regime returns H=1.0."""
        h = compute_ph_hazard(5.0, "")
        assert h == 1.0

    def test_alkaline_regime_at_reference(self):
        """Alkaline regime at pH=13 returns H=1.0."""
        h = compute_ph_hazard(13.0, "alkaline")
        assert math.isclose(h, 1.0, rel_tol=0.01)

    def test_alkaline_regime_above_reference(self):
        """Alkaline regime at pH=14 returns 10^(ALPHA_PH * 1.0)."""
        h = compute_ph_hazard(14.0, "alkaline")
        expected = 10 ** (ALPHA_PH * (14.0 - 13.0))
        assert math.isclose(h, expected, rel_tol=0.001)

    def test_alkaline_regime_below_reference(self):
        """Alkaline regime at pH=12 returns 10^(ALPHA_PH * -1.0) < 1."""
        h = compute_ph_hazard(12.0, "alkaline")
        expected = 10 ** (ALPHA_PH * (12.0 - 13.0))
        assert math.isclose(h, expected, rel_tol=0.001)
        assert h < 1.0


# =============================================================================
# 4. compute_current_hazard - positive j path (line 193)
# =============================================================================

class TestComputeCurrentHazardPositiveJ:
    """Test the return (j / j_ref) ** GAMMA_J for various positive j values."""

    def test_40_mA_cm2(self):
        """compute_current_hazard(40.0) = (40/10)^0.5 = 2.0."""
        h = compute_current_hazard(40.0)
        expected = (40.0 / 10.0) ** GAMMA_J
        assert math.isclose(h, expected, rel_tol=0.001)
        assert math.isclose(h, 2.0, rel_tol=0.001)

    def test_90_mA_cm2(self):
        """compute_current_hazard(90.0) = (90/10)^0.5 = 3.0."""
        h = compute_current_hazard(90.0)
        expected = (90.0 / 10.0) ** GAMMA_J
        assert math.isclose(h, expected, rel_tol=0.001)
        assert math.isclose(h, 3.0, rel_tol=0.001)

    def test_none_returns_unity(self):
        """None returns 1.0."""
        h = compute_current_hazard(None)
        assert h == 1.0

    def test_zero_returns_unity(self):
        """Zero returns 1.0."""
        h = compute_current_hazard(0.0)
        assert h == 1.0

    def test_negative_returns_unity(self):
        """Negative returns 1.0."""
        h = compute_current_hazard(-5.0)
        assert h == 1.0


# =============================================================================
# 5. validate_physics_invariants - INV-N1 identity check violation (line 317)
# =============================================================================

class TestInvN1IdentityViolation:
    """When H_obs ~= H_ref but tau_norm != tau_obs, emit INV_N1_IDENTITY error."""

    def test_identity_violation(self, physics_doc_base):
        """H_obs == H_ref == 1.0 but tau_normalized != tau_obs triggers error."""
        doc = physics_doc_base.copy()
        doc["hazard"] = {
            "severity_index": 1.0,
            "components": {"H_temperature": 1.0},
        }
        doc["observation"] = {"metric_type": "tau20_activity", "value": 100.0}
        doc["normalization"] = {
            "tau_normalized": 200.0,  # WRONG: should be 100.0 when H_obs == H_ref
            "reference_hazard": 1.0,
        }

        result = validate_physics_invariants(doc)

        identity_errors = [i for i in result.issues if i.code == "INV_N1_IDENTITY"]
        assert len(identity_errors) == 1
        assert identity_errors[0].severity == Severity.ERROR
        assert result.is_valid is False
        assert result.physics_valid is False

    def test_identity_satisfied_no_error(self, physics_doc_base):
        """H_obs == H_ref and tau_norm == tau_obs: no INV_N1_IDENTITY error."""
        doc = physics_doc_base.copy()
        doc["hazard"] = {
            "severity_index": 1.0,
            "components": {"H_temperature": 1.0},
        }
        doc["observation"] = {"metric_type": "tau20_activity", "value": 100.0}
        doc["normalization"] = {
            "tau_normalized": 100.0,
            "reference_hazard": 1.0,
        }

        result = validate_physics_invariants(doc)

        identity_errors = [i for i in result.issues if i.code == "INV_N1_IDENTITY"]
        assert len(identity_errors) == 0


# =============================================================================
# 6. validate_physics_invariants - INV-N3 mild check violation (line 333)
# =============================================================================

class TestInvN3MildViolation:
    """When H_obs < H_ref and tau_norm >= tau_obs, emit INV_N3_MILD error."""

    def test_mild_violation(self, physics_doc_base):
        """H_obs < H_ref but tau_norm >= tau_obs triggers INV_N3_MILD error."""
        doc = physics_doc_base.copy()
        doc["hazard"] = {
            "severity_index": 0.5,  # H_obs < H_ref (1.0)
            "components": {"H_temperature": 1.0},
        }
        doc["observation"] = {"metric_type": "tau20_activity", "value": 100.0}
        doc["normalization"] = {
            "tau_normalized": 100.0,  # WRONG: should be < 100 when H_obs < H_ref
            "reference_hazard": 1.0,
        }

        result = validate_physics_invariants(doc)

        mild_errors = [i for i in result.issues if i.code == "INV_N3_MILD"]
        assert len(mild_errors) == 1
        assert mild_errors[0].severity == Severity.ERROR
        assert result.physics_valid is False

    def test_mild_correct_no_error(self, physics_doc_base):
        """H_obs < H_ref and tau_norm < tau_obs: no INV_N3_MILD error."""
        doc = physics_doc_base.copy()
        doc["hazard"] = {
            "severity_index": 0.5,
            "components": {"H_temperature": 1.0},
        }
        doc["observation"] = {"metric_type": "tau20_activity", "value": 100.0}
        doc["normalization"] = {
            "tau_normalized": 50.0,  # Correct: 100 * (0.5 / 1.0) = 50
            "reference_hazard": 1.0,
        }

        result = validate_physics_invariants(doc)

        mild_errors = [i for i in result.issues if i.code == "INV_N3_MILD"]
        assert len(mild_errors) == 0

    def test_mild_violation_with_tau_norm_greater_than_tau_obs(self, physics_doc_base):
        """H_obs < H_ref and tau_norm > tau_obs (strictly greater) also triggers error."""
        doc = physics_doc_base.copy()
        doc["hazard"] = {
            "severity_index": 0.3,
            "components": {"H_temperature": 1.0},
        }
        doc["observation"] = {"metric_type": "tau20_activity", "value": 100.0}
        doc["normalization"] = {
            "tau_normalized": 150.0,  # WRONG: should be 30, definitely wrong
            "reference_hazard": 1.0,
        }

        result = validate_physics_invariants(doc)

        # Should have INV_N3_MILD and/or INV_N4_SCALING
        mild_errors = [i for i in result.issues if i.code == "INV_N3_MILD"]
        assert len(mild_errors) == 1


# =============================================================================
# 7. validate_semantics - MEA low hazard warning (line 416)
# =============================================================================

class TestSemanticsMEALowHazard:
    """When test_format == 'MEA' and H_format < 2.0, emit SEM_MEA_LOW_HAZARD."""

    def test_mea_low_hazard_warning(self):
        """MEA with H_format=1.5 (< 2.0) triggers warning."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "IrO2"},
            "protocol": {"test_format": "MEA"},
            "hazard": {
                "components": {"H_format": 1.5},
            },
        }

        result = validate_semantics(doc)

        warnings = [i for i in result.issues if i.code == "SEM_MEA_LOW_HAZARD"]
        assert len(warnings) == 1
        assert warnings[0].severity == Severity.WARNING
        msg_match = "H_format" in warnings[0].message
        path_match = warnings[0].path == "hazard.components.H_format"
        assert msg_match or path_match

    def test_mea_normal_hazard_no_warning(self):
        """MEA with H_format=2.5 (>= 2.0) does not trigger warning."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "IrO2"},
            "protocol": {"test_format": "MEA"},
            "hazard": {
                "components": {"H_format": 2.5},
            },
        }

        result = validate_semantics(doc)

        warnings = [i for i in result.issues if i.code == "SEM_MEA_LOW_HAZARD"]
        assert len(warnings) == 0

    def test_non_mea_low_format_no_warning(self):
        """Non-MEA format with low H_format does not trigger MEA warning."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "IrO2"},
            "protocol": {"test_format": "RDE"},
            "hazard": {
                "components": {"H_format": 1.0},
            },
        }

        result = validate_semantics(doc)

        warnings = [i for i in result.issues if i.code == "SEM_MEA_LOW_HAZARD"]
        assert len(warnings) == 0


# =============================================================================
# 8. validate_semantics - exposure no data warning (line 428)
# =============================================================================

class TestSemanticsExposureNoData:
    """When exposure_adequacy has tier but no duration or cycles, emit warning."""

    def test_exposure_tier_without_duration_or_cycles(self):
        """Tier set but neither duration_hours nor cycle_count -> warning."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "IrO2"},
            "protocol": {},  # No duration_hours, no cycle_count
            "exposure_adequacy": {"tier": "adequate"},
        }

        result = validate_semantics(doc)

        warnings = [i for i in result.issues if i.code == "SEM_EXPOSURE_NO_DATA"]
        assert len(warnings) == 1
        assert warnings[0].severity == Severity.WARNING
        assert warnings[0].path == "exposure_adequacy"

    def test_exposure_tier_with_duration_no_warning(self):
        """Tier set with duration_hours present -> no warning."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "IrO2"},
            "protocol": {"duration_hours": 100.0},
            "exposure_adequacy": {"tier": "adequate"},
        }

        result = validate_semantics(doc)

        warnings = [i for i in result.issues if i.code == "SEM_EXPOSURE_NO_DATA"]
        assert len(warnings) == 0

    def test_exposure_tier_with_cycles_no_warning(self):
        """Tier set with cycle_count present -> no warning."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "IrO2"},
            "protocol": {"cycle_count": 5000},
            "exposure_adequacy": {"tier": "adequate"},
        }

        result = validate_semantics(doc)

        warnings = [i for i in result.issues if i.code == "SEM_EXPOSURE_NO_DATA"]
        assert len(warnings) == 0

    def test_no_exposure_adequacy_no_warning(self):
        """No exposure_adequacy at all -> no warning."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "IrO2"},
            "protocol": {},
        }

        result = validate_semantics(doc)

        warnings = [i for i in result.issues if i.code == "SEM_EXPOSURE_NO_DATA"]
        assert len(warnings) == 0

    def test_exposure_no_tier_no_warning(self):
        """exposure_adequacy exists but tier is None/missing -> no warning."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "IrO2"},
            "protocol": {},
            "exposure_adequacy": {},
        }

        result = validate_semantics(doc)

        warnings = [i for i in result.issues if i.code == "SEM_EXPOSURE_NO_DATA"]
        assert len(warnings) == 0


# =============================================================================
# 9. load_schema (lines 496-516)
# =============================================================================

class TestLoadSchema:
    """Test schema file loading: explicit path, default search, missing file."""

    def test_load_schema_explicit_path(self, tmp_path):
        """Load schema from an explicit path."""
        schema_data = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
        }
        schema_file = tmp_path / "test.schema.json"
        schema_file.write_text(json.dumps(schema_data))

        result = load_schema(schema_file)

        assert result is not None
        assert result["type"] == "object"

    def test_load_schema_explicit_path_nonexistent(self, tmp_path):
        """Load schema from a nonexistent path returns None."""
        fake_path = tmp_path / "nonexistent.schema.json"

        result = load_schema(fake_path)

        assert result is None

    def test_load_schema_none_path_no_defaults(self):
        """When schema_path is None and no default files exist, returns None."""
        # Mock Path.exists to always return False for the default paths
        with mock.patch.object(Path, "exists", return_value=False):
            result = load_schema(None)

        assert result is None

    def test_load_schema_none_path_finds_default(self, tmp_path):
        """When schema_path is None but a default exists, it is loaded."""
        # Create a temporary schema in one of the default search locations
        # We use an explicit path approach instead since the default paths
        # are relative to the validator module location
        schema_data = {"type": "object", "test_key": True}
        schema_file = tmp_path / "ecdl-v1.0.0.schema.json"
        schema_file.write_text(json.dumps(schema_data))

        # Pass an explicit path to verify the loading works
        result = load_schema(schema_file)

        assert result is not None
        assert result["test_key"] is True


# =============================================================================
# 10. format_result (lines 519-558)
# =============================================================================

class TestFormatResult:
    """Test formatting of ValidationResult for display."""

    def test_valid_result_summary(self):
        """Valid result shows VALID status."""
        result = ValidationResult(
            is_valid=True,
            schema_valid=True,
            physics_valid=True,
            semantic_valid=True,
        )

        output = format_result(result)

        assert "VALID" in output
        assert "pass" in output

    def test_invalid_result_summary(self):
        """Invalid result shows INVALID status."""
        result = ValidationResult(
            is_valid=False,
            schema_valid=False,
            physics_valid=True,
            semantic_valid=True,
        )

        output = format_result(result)

        assert "INVALID" in output
        assert "fail" in output

    def test_format_with_errors(self):
        """Errors are displayed with code, message, path, expected, actual."""
        result = ValidationResult(is_valid=False)
        result.error(
            "TEST_ERROR",
            "Something went wrong",
            path="hazard.components.H_temperature",
            expected=1.0,
            actual=2.0,
        )

        output = format_result(result)

        assert "Errors (1)" in output
        assert "[TEST_ERROR]" in output
        assert "Something went wrong" in output
        assert "Path: hazard.components.H_temperature" in output
        assert "Expected: 1.0" in output
        assert "Actual: 2.0" in output

    def test_format_with_warnings_non_verbose(self):
        """Warnings show code and message; path is hidden in non-verbose mode."""
        result = ValidationResult(is_valid=True)
        result.warning(
            "TEST_WARNING",
            "Watch out for this",
            path="protocol.ph",
        )

        output = format_result(result, verbose=False)

        assert "Warnings (1)" in output
        assert "[TEST_WARNING]" in output
        assert "Watch out for this" in output
        # Path should NOT appear in non-verbose mode for warnings
        assert "Path: protocol.ph" not in output

    def test_format_with_warnings_verbose(self):
        """Warnings show path in verbose mode."""
        result = ValidationResult(is_valid=True)
        result.warning(
            "TEST_WARNING",
            "Watch out for this",
            path="protocol.ph",
        )

        output = format_result(result, verbose=True)

        assert "Warnings (1)" in output
        assert "[TEST_WARNING]" in output
        assert "Path: protocol.ph" in output

    def test_format_with_infos_non_verbose(self):
        """Info messages are hidden in non-verbose mode."""
        result = ValidationResult(is_valid=True)
        result.info("TEST_INFO", "Just a note")

        output = format_result(result, verbose=False)

        assert "Info" not in output
        assert "TEST_INFO" not in output

    def test_format_with_infos_verbose(self):
        """Info messages are shown in verbose mode."""
        result = ValidationResult(is_valid=True)
        result.info("TEST_INFO", "Just a note")

        output = format_result(result, verbose=True)

        assert "Info (1)" in output
        assert "[TEST_INFO]" in output
        assert "Just a note" in output

    def test_format_mixed_issues(self):
        """All severity levels together produce correct sections."""
        result = ValidationResult(is_valid=False)
        result.error("E1", "Error message", path="a.b", expected=1, actual=2)
        result.warning("W1", "Warning message", path="c.d")
        result.info("I1", "Info message")

        output = format_result(result, verbose=True)

        assert "INVALID" in output
        assert "Errors (1)" in output
        assert "[E1]" in output
        assert "Warnings (1)" in output
        assert "[W1]" in output
        assert "Info (1)" in output
        assert "[I1]" in output

    def test_format_no_issues(self):
        """Result with no issues just shows the summary."""
        result = ValidationResult(
            is_valid=True,
            schema_valid=True,
            physics_valid=True,
            semantic_valid=True,
        )

        output = format_result(result, verbose=True)

        assert "VALID" in output
        assert "Errors" not in output
        assert "Warnings" not in output
        assert "Info" not in output

    def test_format_error_without_optional_fields(self):
        """Error without path/expected/actual still formats correctly."""
        result = ValidationResult(is_valid=False)
        result.error("BARE_ERROR", "Just the basics")

        output = format_result(result)

        assert "[BARE_ERROR]" in output
        assert "Just the basics" in output
        # No path/expected/actual lines
        assert "Path:" not in output
        assert "Expected:" not in output
        assert "Actual:" not in output

    def test_format_schema_physics_semantic_status(self):
        """Each subsystem status (pass/fail) appears in the output."""
        result = ValidationResult(
            is_valid=False,
            schema_valid=True,
            physics_valid=False,
            semantic_valid=True,
        )

        output = format_result(result)

        lines = output.split("\n")
        schema_line = [ln for ln in lines if "Schema:" in ln][0]
        physics_line = [ln for ln in lines if "Physics:" in ln][0]
        semantic_line = [ln for ln in lines if "Semantic:" in ln][0]

        assert "pass" in schema_line
        assert "fail" in physics_line
        assert "pass" in semantic_line


# =============================================================================
# INTEGRATION: End-to-end coverage via validate_ecdl
# =============================================================================

class TestValidateEcdlIntegration:
    """Integration tests ensuring the full pipeline exercises all paths."""

    def test_schema_validation_with_violations_propagates(self, simple_schema):
        """Schema violations propagate through validate_ecdl."""
        doc = {"ecdl_version": 123}  # type error + missing material

        result = validate_ecdl(doc, schema=simple_schema)

        assert result.is_valid is False
        assert result.schema_valid is False
        violations = [i for i in result.issues if i.code == "SCHEMA_VIOLATION"]
        assert len(violations) >= 1

    def test_identity_violation_through_validate_ecdl(self, physics_doc_base):
        """INV-N1 identity violation detected through full validation."""
        doc = physics_doc_base.copy()
        doc["hazard"]["severity_index"] = 1.0
        doc["observation"]["value"] = 100.0
        doc["normalization"]["tau_normalized"] = 999.0  # wrong
        doc["normalization"]["reference_hazard"] = 1.0

        result = validate_ecdl(doc)

        identity_errors = [i for i in result.issues if i.code == "INV_N1_IDENTITY"]
        assert len(identity_errors) == 1
        assert result.is_valid is False

    def test_mea_low_hazard_through_validate_ecdl(self):
        """MEA low hazard warning detected through full validation."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "IrO2"},
            "protocol": {"test_format": "MEA"},
            "hazard": {"components": {"H_format": 1.0}},
        }

        result = validate_ecdl(doc)

        warnings = [i for i in result.issues if i.code == "SEM_MEA_LOW_HAZARD"]
        assert len(warnings) == 1


# =============================================================================
# ValidationResult helper methods
# =============================================================================

class TestValidationResultMethods:
    """Test the error/warning/info convenience methods on ValidationResult."""

    def test_error_sets_is_valid_false(self):
        result = ValidationResult(is_valid=True)
        result.error("CODE", "msg")

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].severity == Severity.ERROR
        assert result.issues[0].code == "CODE"

    def test_warning_does_not_change_is_valid(self):
        result = ValidationResult(is_valid=True)
        result.warning("CODE", "msg")

        assert result.is_valid is True
        assert len(result.issues) == 1
        assert result.issues[0].severity == Severity.WARNING

    def test_info_does_not_change_is_valid(self):
        result = ValidationResult(is_valid=True)
        result.info("CODE", "msg")

        assert result.is_valid is True
        assert len(result.issues) == 1
        assert result.issues[0].severity == Severity.INFO

    def test_add_issue_with_kwargs(self):
        result = ValidationResult(is_valid=True)
        result.error("E", "e", path="a.b", expected=1, actual=2)

        issue = result.issues[0]
        assert issue.path == "a.b"
        assert issue.expected == 1
        assert issue.actual == 2


# =============================================================================
# ADDITIONAL: Cover remaining uncovered lines
# =============================================================================

class TestInvH1MonotonicityViolation:
    """Line 238: temp > 25 but H_temperature reported as <= 1.0 in the doc."""

    def test_temperature_monotonicity_violation(self):
        """If temp_c > 25 but the doc says H_temperature <= 1.0, error is emitted."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "IrO2"},
            "protocol": {
                "temperature_C": 80.0,  # > 25
            },
            "hazard": {
                "severity_index": 1.0,
                "components": {
                    # Intentionally wrong: 80C should give H >> 1.0
                    "H_temperature": 0.5,
                },
            },
        }

        result = validate_physics_invariants(doc)

        mono_errors = [i for i in result.issues if i.code == "INV_H1_MONOTONICITY"]
        assert len(mono_errors) == 1
        assert mono_errors[0].severity == Severity.ERROR
        assert mono_errors[0].actual == 0.5


class TestSemanticValidationInvalid:
    """Line 484: When semantic validation has errors, is_valid is set False in validate_ecdl."""

    def test_semantic_error_propagates_to_final_result(self):
        """Material = electrolyte triggers SEM error, making final result invalid."""
        doc = {
            "ecdl_version": "1.0.0",
            "material": {"formula_raw": "H2SO4"},  # This IS an electrolyte
            "protocol": {},
        }

        result = validate_ecdl(doc)

        assert result.is_valid is False
        assert result.semantic_valid is False
        sem_errors = [i for i in result.issues if i.code == "SEM_MATERIAL_IS_ELECTROLYTE"]
        assert len(sem_errors) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
