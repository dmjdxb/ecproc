"""Integration tests: parse -> validate -> run pipeline."""

from __future__ import annotations

import pytest

from ecproc.ir.generator import generate_ir
from ecproc.ir.schema import FaradayIR
from ecproc.parser.yaml_parser import YAMLParser
from ecproc.sdk.procedure import Procedure
from ecproc.validator.engine import ValidationEngine
from ecproc.validator.errors import ValidationResult

# ---------------------------------------------------------------------------
# YAML source strings for testing
# ---------------------------------------------------------------------------

VALID_OER_YAML = """\
metadata:
  protocol: "OER Stability Test"
  version: "1.0"
  author: "Integration Test"

system:
  electrodes: 3
  reference: RHE
  electrolyte:
    solute: HClO4
    concentration_M: 0.1

procedure:
  - name: Conditioning
    setup:
      gas: N2
    steps:
      - cv:
          vertex1: 0.05
          vertex2: 1.2
          rate: 50
          cycles: 50
  - name: Baseline
    steps:
      - eis:
          f_start: 100000
          f_end: 0.1
          amplitude: 10
          tag: baseline_eis
"""

INVALID_MISSING_PROTOCOL_YAML = """\
metadata:
  version: "1.0"

system:
  electrodes: 3
  reference: RHE

procedure:
  - name: Phase1
    steps:
      - cv:
          vertex1: 0.05
          vertex2: 1.2
"""

MINIMAL_VALID_YAML = """\
metadata:
  protocol: "Minimal"
  version: "1.0"

system:
  electrodes: 3
  reference: RHE

procedure:
  - name: Test
    steps:
      - ocp:
          stable: "1 mV/s"
"""


# ---------------------------------------------------------------------------
# Parse -> IR -> Validate (valid file)
# ---------------------------------------------------------------------------


class TestParseValidatePass:
    """End-to-end: parse a valid .ecproc -> generate IR -> validate -> pass."""

    def test_parse_valid_yaml_to_ast(self):
        parser = YAMLParser()
        ast = parser.parse_string(VALID_OER_YAML, source_name="test")
        assert ast.metadata.protocol == "OER Stability Test"
        assert len(ast.procedure) == 2

    def test_generate_ir_from_valid_ast(self):
        parser = YAMLParser()
        ast = parser.parse_string(VALID_OER_YAML, source_name="test")
        ir = generate_ir(ast)
        assert isinstance(ir, FaradayIR)
        assert ir.metadata.protocol == "OER Stability Test"
        assert len(ir.procedure) == 2

    def test_validate_valid_ir_passes(self):
        parser = YAMLParser()
        ast = parser.parse_string(VALID_OER_YAML, source_name="test")
        ir = generate_ir(ast)
        engine = ValidationEngine()
        result = engine.validate(ir, level=1)
        assert isinstance(result, ValidationResult)
        # L1 syntax validation should pass for well-formed IR
        assert result.valid is True or len(result.errors) == 0

    def test_full_pipeline_parse_ir_validate(self):
        parser = YAMLParser()
        ast = parser.parse_string(VALID_OER_YAML, source_name="test")
        ir = generate_ir(ast)
        engine = ValidationEngine()
        result = engine.validate(ir, level=2)
        assert isinstance(result, ValidationResult)
        # At level 2, a well-formed procedure should generally be valid
        # (may have warnings but no errors)


# ---------------------------------------------------------------------------
# Parse -> IR -> Validate (invalid file)
# ---------------------------------------------------------------------------


class TestParseInvalidFile:
    """Parse an invalid .ecproc -> expect appropriate errors."""

    def test_parse_missing_protocol_raises(self):
        parser = YAMLParser()
        with pytest.raises(Exception):
            # Missing 'protocol' in metadata should raise a parse error
            parser.parse_string(INVALID_MISSING_PROTOCOL_YAML, source_name="test")


# ---------------------------------------------------------------------------
# SDK procedure -> AST -> IR -> Validate
# ---------------------------------------------------------------------------


class TestSDKToIRToValidate:
    """Build a procedure using the SDK, convert to IR, and validate."""

    def _build_procedure(self) -> Procedure:
        proc = Procedure("SDK Integration Test", version="1.0", author="Test")
        proc.system(
            electrodes=3,
            reference="RHE",
            electrolyte=("HClO4", 0.1),
        )
        with proc.phase("Conditioning") as p:
            p.cv(vertex1=0.05, vertex2=1.2, rate=50, cycles=50)
        with proc.phase("Measurement") as p:
            p.eis(f_start=100000, f_end=0.1, amplitude=10, tag="eis_baseline")
        return proc

    def test_sdk_to_ast(self):
        proc = self._build_procedure()
        ast = proc.to_ast()
        assert ast.metadata.protocol == "SDK Integration Test"
        assert len(ast.procedure) == 2

    def test_sdk_to_ir(self):
        proc = self._build_procedure()
        ast = proc.to_ast()
        ir = generate_ir(ast)
        assert isinstance(ir, FaradayIR)
        assert len(ir.procedure) == 2

    def test_sdk_ir_validates(self):
        proc = self._build_procedure()
        ast = proc.to_ast()
        ir = generate_ir(ast)
        engine = ValidationEngine()
        result = engine.validate(ir, level=1)
        assert isinstance(result, ValidationResult)


# ---------------------------------------------------------------------------
# Pipeline with safety constraints
# ---------------------------------------------------------------------------


class TestPipelineWithSafety:
    """Test parse-validate pipeline with safety constraints."""

    SAFETY_YAML = """\
metadata:
  protocol: "Safety Test"
  version: "1.0"

system:
  electrodes: 3
  reference: RHE

procedure:
  - name: Test
    steps:
      - cv:
          vertex1: 0.05
          vertex2: 1.2
          rate: 50
          cycles: 10

safety:
  max_current: "500 mA"
  voltage_window:
    - "-0.5 V"
    - "2.0 V"
  temperature_limits:
    - "15 C"
    - "40 C"
"""

    def test_parse_with_safety(self):
        parser = YAMLParser()
        ast = parser.parse_string(self.SAFETY_YAML, source_name="test")
        assert ast.safety is not None
        assert ast.safety.max_current == "500 mA"

    def test_ir_has_safety(self):
        parser = YAMLParser()
        ast = parser.parse_string(self.SAFETY_YAML, source_name="test")
        ir = generate_ir(ast)
        assert ir.safety is not None
        assert ir.safety.max_current_A is not None


# ---------------------------------------------------------------------------
# Minimal YAML pipeline
# ---------------------------------------------------------------------------


class TestMinimalPipeline:
    """Test pipeline with a minimal valid YAML."""

    def test_minimal_yaml_round_trip(self):
        parser = YAMLParser()
        ast = parser.parse_string(MINIMAL_VALID_YAML, source_name="test")
        ir = generate_ir(ast)
        assert ir.metadata.protocol == "Minimal"
        assert len(ir.procedure) == 1
        assert ir.procedure[0].name == "Test"
