"""Comprehensive tests for the ecproc YAML parser.

Tests cover:
- Basic parsing of valid simple, complex, and DOE ORR fixtures
- Range syntax, value+unit, and duration parsing
- Phase structure (setup/stabilize/steps/teardown)
- Step tags, extract fields (string and dict forms)
- Vendor flags
- Checkpoints with triggers (any/all combiners)
- Loops with steps, checkpoint, and stop_if
- State recovery parsing
- Output section parsing
- Variable template preservation
- Source line tracking
- Error handling for missing fields, unknown techniques, and invalid structures
- Working electrode and electrolyte parsing
- Safety section with thermal_runaway and reference_electrode_monitor
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ecproc.parser.ast import (
    ElectrolyteAST,
    LoopAST,
    ProcedureAST,
    ReferenceMonitorAST,
    SourceLocation,
    StepAST,
    ThermalRunawayAST,
    WorkingElectrodeAST,
)
from ecproc.parser.errors import (
    MissingFieldError,
    UnknownTechniqueError,
    YAMLStructureError,
)
from ecproc.parser.yaml_parser import YAMLParser

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def parser() -> YAMLParser:
    """Return a fresh YAMLParser instance."""
    return YAMLParser()


# ===================================================================
# 1. Basic valid-file parsing
# ===================================================================


class TestParseValidSimple:
    """Tests against valid_simple.ecproc."""

    def test_parse_simple_file(self, parser: YAMLParser) -> None:
        """Parse simple valid file and verify top-level structure."""
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        assert isinstance(ast, ProcedureAST)
        assert ast.metadata.protocol == "Simple CV"
        assert ast.metadata.version == "1.0"
        assert ast.metadata.author == "Test User"

    def test_simple_system(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        assert ast.system.electrodes == 3
        assert ast.system.reference == "RHE"
        assert ast.system.working is None
        assert ast.system.electrolyte is None

    def test_simple_single_phase(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        assert len(ast.procedure) == 1
        phase = ast.procedure[0]
        assert phase.name == "Conditioning"

    def test_simple_cv_step(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        phase = ast.procedure[0]
        assert len(phase.steps) == 1
        step = phase.steps[0]
        assert isinstance(step, StepAST)
        assert step.technique == "cv"

    def test_simple_cv_parameters_preserved(self, parser: YAMLParser) -> None:
        """Parser preserves value+unit strings as-is; no unit conversion at parse time."""
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        step = ast.procedure[0].steps[0]
        assert isinstance(step, StepAST)
        params = step.parameters
        assert "between" in params
        assert params["between"] == "0.05 V and 1.2 V"
        assert params["rate"] == "50 mV/s"
        assert params["cycles"] == 20

    def test_simple_source_file_set(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        assert ast.source_file is not None
        assert ast.source_file.name == "valid_simple.ecproc"

    def test_simple_no_safety(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        assert ast.safety is None

    def test_simple_no_state_recovery(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        assert ast.state_recovery is None

    def test_simple_no_output(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        assert ast.output is None


# ===================================================================
# 2. Complex valid-file parsing
# ===================================================================


class TestParseValidComplex:
    """Tests against valid_complex.ecproc."""

    def test_parse_complex_file(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        assert isinstance(ast, ProcedureAST)
        assert ast.metadata.protocol == "Complex Multi-Phase Experiment"
        assert ast.metadata.version == "2.3"

    def test_complex_metadata_optional_fields(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        assert ast.metadata.author == "Dr. Smith"
        assert ast.metadata.electrolyte == "0.1 M HClO4"
        assert ast.metadata.gas == "N2"
        assert ast.metadata.notes == "Full-featured test fixture"

    def test_complex_multiple_phases(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        assert len(ast.procedure) == 5
        names = [p.name for p in ast.procedure]
        assert names == [
            "Setup Phase",
            "Stabilize Phase",
            "Measurement Phase",
            "Durability Phase",
            "Endurance Phase",
        ]

    def test_phase_setup(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        setup_phase = ast.procedure[0]
        assert setup_phase.setup is not None
        assert setup_phase.setup["gas"] == "N2"
        assert setup_phase.setup["rotation"] == 1600

    def test_phase_stabilize(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        setup_phase = ast.procedure[0]
        assert setup_phase.stabilize is not None
        assert isinstance(setup_phase.stabilize, list)
        assert len(setup_phase.stabilize) == 1
        assert "OCP stable within 5 mV for 60 s" in setup_phase.stabilize[0]

    def test_phase_teardown(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        setup_phase = ast.procedure[0]
        assert setup_phase.teardown is not None
        # YAML parses `off` as boolean False
        assert setup_phase.teardown["gas"] in ("off", False)

    def test_tag_on_step(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        # Setup Phase, second step (eis with tag)
        eis_step = ast.procedure[0].steps[1]
        assert isinstance(eis_step, StepAST)
        assert eis_step.tag == "setup_eis"

    def test_extract_string_form(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        eis_step = ast.procedure[0].steps[1]
        assert isinstance(eis_step, StepAST)
        assert eis_step.extract == "Ru"

    def test_extract_dict_form(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        # Measurement Phase, first step (eis with dict extract)
        meas_eis = ast.procedure[2].steps[0]
        assert isinstance(meas_eis, StepAST)
        assert isinstance(meas_eis.extract, dict)
        assert meas_eis.extract["Ru"] == "high_frequency_intercept"
        assert meas_eis.extract["Rct"] == "semicircle_diameter"

    def test_vendor_flags(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        eis_step = ast.procedure[0].steps[1]
        assert isinstance(eis_step, StepAST)
        assert eis_step.vendor_flags is not None
        assert "biologic" in eis_step.vendor_flags
        assert eis_step.vendor_flags["biologic"]["bandwidth"] == 5
        assert eis_step.vendor_flags["biologic"]["drift_correction"] is True
        assert "gamry" in eis_step.vendor_flags
        assert eis_step.vendor_flags["gamry"]["ac_settling"] == 3

    def test_loop_with_checkpoint_any_triggers(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        durability = ast.procedure[3]
        assert len(durability.steps) == 1
        loop = durability.steps[0]
        assert isinstance(loop, LoopAST)
        assert loop.count == 30000
        assert loop.checkpoint is not None
        assert loop.checkpoint.logic == "any"
        assert len(loop.checkpoint.triggers) == 2

    def test_loop_checkpoint_trigger_types(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        loop = ast.procedure[3].steps[0]
        assert isinstance(loop, LoopAST)
        triggers = loop.checkpoint.triggers
        # First trigger: every 5000 cycles
        assert triggers[0].type == "every_cycles"
        assert triggers[0].value == 5000
        assert triggers[0].unit == "cycles"
        # Second trigger: every 24 h
        assert triggers[1].type == "every_time"
        assert triggers[1].value == 24
        assert triggers[1].unit == "h"

    def test_loop_checkpoint_do_list(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        loop = ast.procedure[3].steps[0]
        assert isinstance(loop, LoopAST)
        do_items = loop.checkpoint.do
        assert len(do_items) == 2
        assert isinstance(do_items[0], StepAST)
        assert do_items[0].technique == "eis"
        assert isinstance(do_items[1], StepAST)
        assert do_items[1].technique == "cv"
        assert do_items[1].tag == "checkpoint_cv"

    def test_loop_with_variable_count(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        endurance = ast.procedure[4]
        loop = endurance.steps[0]
        assert isinstance(loop, LoopAST)
        assert loop.count == "{total_cycles}"

    def test_loop_stop_if(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        loop = ast.procedure[4].steps[0]
        assert isinstance(loop, LoopAST)
        assert loop.stop_if == "ECSA_loss > 40%"

    def test_state_recovery_after_pause(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        sr = ast.state_recovery
        assert sr is not None
        assert sr.after_pause is not None
        assert len(sr.after_pause) == 1
        assert sr.after_pause[0].technique == "ocp"

    def test_state_recovery_after_checkpoint(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        sr = ast.state_recovery
        assert sr.after_checkpoint is not None
        assert len(sr.after_checkpoint) == 2
        assert sr.after_checkpoint[0].technique == "ocp"
        assert sr.after_checkpoint[1].technique == "eis"

    def test_state_recovery_after_error(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        sr = ast.state_recovery
        assert sr.after_error is not None
        assert len(sr.after_error) == 2
        # First item is a string
        assert isinstance(sr.after_error[0], str)
        assert sr.after_error[0] == "log_error"
        # Second item is a step
        assert isinstance(sr.after_error[1], StepAST)
        assert sr.after_error[1].technique == "ocp"

    def test_output_section(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        assert ast.output is not None
        assert ast.output.ecdl is not None
        assert ast.output.ecdl["include_raw"] is True
        assert ast.output.ecdl["compress"] == "gzip"
        assert ast.output.ecdl["signing"] == "sha256"

    def test_safety_max_current(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        assert ast.safety is not None
        assert ast.safety.max_current == "200 mA"

    def test_safety_voltage_window(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        assert ast.safety.voltage_window == ["-0.5 V", "2.0 V"]

    def test_safety_temperature_limits(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        assert ast.safety.temperature_limits == ["15 C", "40 C"]

    def test_safety_stop_if(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        assert ast.safety.stop_if is not None
        assert len(ast.safety.stop_if) == 2
        assert "current > 500 mA" in ast.safety.stop_if

    def test_safety_thermal_runaway(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        tr = ast.safety.thermal_runaway
        assert tr is not None
        assert isinstance(tr, ThermalRunawayAST)
        assert tr.max_dT_dt == 5.0
        assert tr.action == "emergency_stop"

    def test_safety_reference_electrode_monitor(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        rem = ast.safety.reference_electrode_monitor
        assert rem is not None
        assert isinstance(rem, ReferenceMonitorAST)
        assert rem.max_Ru_change == "10x"
        assert rem.max_ocp_drift == "500 mV/s"
        assert rem.action == "cell_off"


# ===================================================================
# 3. DOE ORR fixture parsing
# ===================================================================


class TestParseDOEORR:
    """Tests against valid_doe_orr.ecproc."""

    def test_parse_doe_orr(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_doe_orr.ecproc")
        assert ast.metadata.protocol == "DOE ORR Catalyst AST"

    def test_doe_orr_five_phases(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_doe_orr.ecproc")
        assert len(ast.procedure) == 5
        expected = [
            "Conditioning",
            "iR Compensation",
            "Background",
            "ORR Activity",
            "Durability",
        ]
        assert [p.name for p in ast.procedure] == expected

    def test_doe_orr_working_electrode(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_doe_orr.ecproc")
        we = ast.system.working
        assert we is not None
        assert isinstance(we, WorkingElectrodeAST)
        assert we.material == "Pt/C"
        assert we.area_cm2 == 0.196
        assert we.loading_ug_cm2 == 20.0

    def test_doe_orr_electrolyte_object(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_doe_orr.ecproc")
        elyte = ast.system.electrolyte
        assert isinstance(elyte, ElectrolyteAST)
        assert elyte.solute == "HClO4"
        assert elyte.concentration_M == 0.1

    def test_doe_orr_counter_electrode(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_doe_orr.ecproc")
        assert ast.system.counter == "Pt mesh"

    def test_doe_orr_purge_step(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_doe_orr.ecproc")
        conditioning = ast.procedure[0]
        purge = conditioning.steps[0]
        assert isinstance(purge, StepAST)
        assert purge.technique == "purge"
        assert purge.parameters["gas"] == "N2"

    def test_doe_orr_durability_loop(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_doe_orr.ecproc")
        durability = ast.procedure[4]
        # After purge step, there is a loop
        loop = durability.steps[1]
        assert isinstance(loop, LoopAST)
        assert loop.count == 30000

    def test_doe_orr_checkpoint_every_5000(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_doe_orr.ecproc")
        loop = ast.procedure[4].steps[1]
        assert isinstance(loop, LoopAST)
        assert loop.checkpoint is not None
        assert len(loop.checkpoint.triggers) == 1
        assert loop.checkpoint.triggers[0].type == "every_cycles"
        assert loop.checkpoint.triggers[0].value == 5000

    def test_doe_orr_checkpoint_do_actions(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_doe_orr.ecproc")
        loop = ast.procedure[4].steps[1]
        assert isinstance(loop, LoopAST)
        do_items = loop.checkpoint.do
        assert len(do_items) == 3
        assert do_items[0].technique == "eis"
        assert do_items[1].technique == "cv"
        assert do_items[1].tag == "durability_cv"
        assert do_items[2].technique == "lsv"
        assert do_items[2].tag == "durability_lsv"

    def test_doe_orr_safety_section(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_doe_orr.ecproc")
        assert ast.safety is not None
        assert ast.safety.max_current == "100 mA"
        assert ast.safety.voltage_window == ["-0.2 V", "1.5 V"]
        assert ast.safety.stop_if is not None
        assert len(ast.safety.stop_if) == 2

    def test_doe_orr_metadata_extra_fields(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_doe_orr.ecproc")
        assert ast.metadata.working_electrode == "Pt/C on GCE"
        assert ast.metadata.reference == "RHE"


# ===================================================================
# 4. Range syntax and value+unit parsing
# ===================================================================


class TestRangeAndValueParsing:
    """Verify that the parser preserves raw value+unit strings."""

    def test_range_syntax_between(self, parser: YAMLParser) -> None:
        """'between: 0.05 V and 1.2 V' preserved as-is."""
        yaml_text = """
metadata:
  protocol: Range Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - cv:
          between: 0.05 V and 1.2 V
          rate: 50 mV/s
          cycles: 3
"""
        ast = parser.parse_string(yaml_text)
        step = ast.procedure[0].steps[0]
        assert step.parameters["between"] == "0.05 V and 1.2 V"

    def test_value_unit_string_rate(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Unit Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - cv:
          between: 0.0 V and 1.0 V
          rate: 100 mV/s
          cycles: 1
"""
        ast = parser.parse_string(yaml_text)
        step = ast.procedure[0].steps[0]
        assert step.parameters["rate"] == "100 mV/s"

    def test_duration_for_syntax(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Duration Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 300 s
"""
        ast = parser.parse_string(yaml_text)
        step = ast.procedure[0].steps[0]
        assert step.parameters["for"] == "300 s"

    def test_duration_minutes(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Duration Min
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - purge:
          gas: N2
          for: 20 min
"""
        ast = parser.parse_string(yaml_text)
        step = ast.procedure[0].steps[0]
        assert step.parameters["for"] == "20 min"


# ===================================================================
# 5. parse_string tests
# ===================================================================


class TestParseString:
    """Tests for parse_string entry point."""

    def test_parse_string_basic(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: String Test
  version: "1.0"
system:
  electrodes: 2
  reference: Ag/AgCl
procedure:
  - name: Phase1
    steps:
      - ocp:
          for: 60 s
"""
        ast = parser.parse_string(yaml_text)
        assert ast.metadata.protocol == "String Test"
        assert ast.system.electrodes == 2
        assert ast.system.reference == "Ag/AgCl"
        assert ast.source_file is None

    def test_parse_string_source_name(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Named
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        ast = parser.parse_string(yaml_text, source_name="test_input")
        # Source name propagates through error messages, not directly on AST.
        # But metadata should parse fine.
        assert ast.metadata.protocol == "Named"


# ===================================================================
# 6. Source line tracking
# ===================================================================


class TestSourceLineTracking:
    """Verify source_location is populated on AST nodes."""

    def test_phase_has_source_location(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        phase = ast.procedure[0]
        assert phase.source_location is not None
        assert isinstance(phase.source_location, SourceLocation)
        assert phase.source_location.line > 0

    def test_step_has_source_location(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        step = ast.procedure[0].steps[0]
        assert isinstance(step, StepAST)
        assert step.source_location is not None
        assert step.source_location.line > 0

    def test_system_has_source_location(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        assert ast.system.source_location is not None
        assert ast.system.source_location.line > 0

    def test_safety_has_source_location(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_complex.ecproc")
        assert ast.safety is not None
        assert ast.safety.source_location is not None
        assert ast.safety.source_location.line > 0

    def test_source_location_file_set(self, parser: YAMLParser) -> None:
        ast = parser.parse_file(FIXTURES / "valid_simple.ecproc")
        phase = ast.procedure[0]
        assert phase.source_location.file is not None
        assert "valid_simple.ecproc" in phase.source_location.file


# ===================================================================
# 7. Error handling
# ===================================================================


class TestErrorHandling:
    """Tests for parser error detection."""

    def test_error_missing_metadata_protocol(self, parser: YAMLParser) -> None:
        """invalid_syntax.ecproc is missing metadata.protocol."""
        with pytest.raises(MissingFieldError, match="protocol"):
            parser.parse_file(FIXTURES / "invalid_syntax.ecproc")

    def test_error_missing_metadata_section(self, parser: YAMLParser) -> None:
        yaml_text = """
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        with pytest.raises(MissingFieldError, match="metadata"):
            parser.parse_string(yaml_text)

    def test_error_missing_system(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Test
  version: "1.0"
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        with pytest.raises(MissingFieldError, match="system"):
            parser.parse_string(yaml_text)

    def test_error_missing_procedure(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
"""
        with pytest.raises(MissingFieldError, match="procedure"):
            parser.parse_string(yaml_text)

    def test_error_empty_procedure(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure: []
"""
        with pytest.raises(YAMLStructureError, match="at least one phase"):
            parser.parse_string(yaml_text)

    def test_error_unknown_technique(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - voltammogram:
          from: 0 V
          to: 1 V
"""
        with pytest.raises(UnknownTechniqueError, match="voltammogram"):
            parser.parse_string(yaml_text)

    def test_error_metadata_not_mapping(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata: "just a string"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        with pytest.raises(YAMLStructureError, match="metadata.*mapping"):
            parser.parse_string(yaml_text)

    def test_error_system_not_mapping(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Test
  version: "1.0"
system: "three electrodes"
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        with pytest.raises(YAMLStructureError, match="system.*mapping"):
            parser.parse_string(yaml_text)

    def test_error_procedure_not_list(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  name: Single Phase
  steps: []
"""
        with pytest.raises(YAMLStructureError, match="procedure.*sequence"):
            parser.parse_string(yaml_text)

    def test_error_missing_phase_name(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - steps:
      - ocp:
          for: 10 s
"""
        with pytest.raises(MissingFieldError, match="name"):
            parser.parse_string(yaml_text)

    def test_error_missing_system_electrodes(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Test
  version: "1.0"
system:
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        with pytest.raises(MissingFieldError, match="electrodes"):
            parser.parse_string(yaml_text)

    def test_error_missing_system_reference(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Test
  version: "1.0"
system:
  electrodes: 3
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        with pytest.raises(MissingFieldError, match="reference"):
            parser.parse_string(yaml_text)

    def test_error_invalid_yaml(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Test
  version: "1.0
"""
        with pytest.raises(YAMLStructureError, match="YAML parse error"):
            parser.parse_string(yaml_text)

    def test_error_non_mapping_top_level(self, parser: YAMLParser) -> None:
        yaml_text = "- just a list"
        with pytest.raises(YAMLStructureError, match="[Tt]op-level"):
            parser.parse_string(yaml_text)

    def test_error_file_not_found(self, parser: YAMLParser) -> None:
        with pytest.raises(FileNotFoundError):
            parser.parse_file(FIXTURES / "nonexistent.ecproc")

    def test_error_vendor_flags_not_mapping(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - cv:
          between: 0.0 V and 1.0 V
          rate: 50 mV/s
          cycles: 1
          vendor_flags: "not a dict"
"""
        with pytest.raises(YAMLStructureError, match="vendor_flags.*mapping"):
            parser.parse_string(yaml_text)


# ===================================================================
# 8. Electrolyte parsing (string and object forms)
# ===================================================================


class TestElectrolyteParsing:
    """Test different electrolyte specification forms."""

    def test_electrolyte_string(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Elyte String
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
  electrolyte: "0.5 M H2SO4"
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        ast = parser.parse_string(yaml_text)
        assert ast.system.electrolyte == "0.5 M H2SO4"

    def test_electrolyte_object(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Elyte Object
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
  electrolyte:
    solute: KOH
    concentration_M: 1.0
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        ast = parser.parse_string(yaml_text)
        elyte = ast.system.electrolyte
        assert isinstance(elyte, ElectrolyteAST)
        assert elyte.solute == "KOH"
        assert elyte.concentration_M == 1.0

    def test_electrolyte_none(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: No Elyte
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        ast = parser.parse_string(yaml_text)
        assert ast.system.electrolyte is None


# ===================================================================
# 9. Working electrode parsing
# ===================================================================


class TestWorkingElectrodeParsing:
    """Test working electrode specification."""

    def test_working_electrode_full(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: WE Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
  working:
    material: IrO2
    area_cm2: 0.071
    loading_ug_cm2: 50.0
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        ast = parser.parse_string(yaml_text)
        we = ast.system.working
        assert we is not None
        assert we.material == "IrO2"
        assert we.area_cm2 == pytest.approx(0.071)
        assert we.loading_ug_cm2 == pytest.approx(50.0)

    def test_working_electrode_material_only(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: WE Min
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
  working:
    material: GCE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        ast = parser.parse_string(yaml_text)
        we = ast.system.working
        assert we is not None
        assert we.material == "GCE"
        assert we.area_cm2 is None
        assert we.loading_ug_cm2 is None


# ===================================================================
# 10. Variable templates
# ===================================================================


class TestVariableTemplates:

    def test_variable_in_loop_count(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Var Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - loop:
          count: "{num_cycles}"
          steps:
            - cv:
                between: 0.0 V and 1.0 V
                rate: 50 mV/s
                cycles: 1
"""
        ast = parser.parse_string(yaml_text)
        loop = ast.procedure[0].steps[0]
        assert isinstance(loop, LoopAST)
        assert loop.count == "{num_cycles}"

    def test_variable_with_dot_notation(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Var Dot
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - loop:
          count: "{config.cycles}"
          steps:
            - ocp:
                for: 10 s
"""
        ast = parser.parse_string(yaml_text)
        loop = ast.procedure[0].steps[0]
        assert isinstance(loop, LoopAST)
        assert loop.count == "{config.cycles}"


# ===================================================================
# 11. Checkpoint variations
# ===================================================================


class TestCheckpointVariations:

    def test_checkpoint_all_combiner(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Checkpoint All
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - loop:
          count: 10000
          steps:
            - cv:
                between: 0.0 V and 1.0 V
                rate: 50 mV/s
                cycles: 1
          checkpoint:
            trigger:
              all:
                - every: 1000 cycles
                - every: 12 h
            do:
              - ocp:
                  for: 30 s
"""
        ast = parser.parse_string(yaml_text)
        loop = ast.procedure[0].steps[0]
        assert isinstance(loop, LoopAST)
        assert loop.checkpoint.logic == "all"
        assert len(loop.checkpoint.triggers) == 2

    def test_checkpoint_as_sibling_to_loop(self, parser: YAMLParser) -> None:
        """Checkpoint can appear as a sibling key to loop, not nested inside."""
        yaml_text = """
metadata:
  protocol: Sibling Checkpoint
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - loop:
          count: 5000
          steps:
            - cv:
                between: 0.0 V and 1.0 V
                rate: 50 mV/s
                cycles: 1
        checkpoint:
          trigger:
            any:
              - every: 1000 cycles
          do:
            - ocp:
                for: 10 s
"""
        ast = parser.parse_string(yaml_text)
        loop = ast.procedure[0].steps[0]
        assert isinstance(loop, LoopAST)
        assert loop.checkpoint is not None
        assert loop.checkpoint.logic == "any"

    def test_checkpoint_single_trigger(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Single Trigger
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - loop:
          count: 100
          steps:
            - ocp:
                for: 5 s
          checkpoint:
            trigger:
              every: 10 cycles
            do:
              - ocp:
                  for: 30 s
"""
        ast = parser.parse_string(yaml_text)
        loop = ast.procedure[0].steps[0]
        assert isinstance(loop, LoopAST)
        assert loop.checkpoint is not None
        assert len(loop.checkpoint.triggers) == 1
        assert loop.checkpoint.triggers[0].type == "every_cycles"
        assert loop.checkpoint.triggers[0].value == 10

    def test_checkpoint_reset_field(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Reset Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - loop:
          count: 100
          steps:
            - ocp:
                for: 1 s
          checkpoint:
            trigger:
              every: 50 cycles
            reset: shared
            do:
              - ocp:
                  for: 5 s
"""
        ast = parser.parse_string(yaml_text)
        loop = ast.procedure[0].steps[0]
        assert isinstance(loop, LoopAST)
        assert loop.checkpoint.reset == "shared"


# ===================================================================
# 12. Known techniques parametrized
# ===================================================================


@pytest.mark.parametrize(
    "technique",
    [
        "cv", "lsv", "eis", "ocp", "hold", "galvanostatic",
        "dpv", "swv", "gcd", "cc", "stripping", "purge",
    ],
)
def test_known_technique_parses(parser: YAMLParser, technique: str) -> None:
    """Every known technique name should be accepted by the parser."""
    yaml_text = f"""
metadata:
  protocol: Technique Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - {technique}:
          value: test
"""
    ast = parser.parse_string(yaml_text)
    step = ast.procedure[0].steps[0]
    assert isinstance(step, StepAST)
    assert step.technique == technique


# ===================================================================
# 13. Invalid fixture files (parse succeeds, validation catches later)
# ===================================================================


class TestInvalidFixturesParseable:
    """Invalid fixtures that parse but may fail validation."""

    def test_invalid_scan_rate_parses(self, parser: YAMLParser) -> None:
        """Parser accepts high scan rate -- validation catches PV001 later."""
        ast = parser.parse_file(FIXTURES / "invalid_scan_rate.ecproc")
        assert isinstance(ast, ProcedureAST)
        step = ast.procedure[0].steps[0]
        assert isinstance(step, StepAST)
        assert step.technique == "cv"
        # The raw parameter is preserved; validator checks constraints.
        assert step.parameters["rate"] == "20000 mV/s"

    def test_invalid_safety_parses(self, parser: YAMLParser) -> None:
        """Parser accepts potential outside window -- safety validator checks."""
        ast = parser.parse_file(FIXTURES / "invalid_safety.ecproc")
        assert isinstance(ast, ProcedureAST)
        assert ast.safety is not None
        assert ast.safety.voltage_window == ["-0.5 V", "2.0 V"]


# ===================================================================
# 14. Edge cases
# ===================================================================


class TestEdgeCases:

    def test_ocp_scalar_shorthand(self, parser: YAMLParser) -> None:
        """ocp: 30 s  (scalar shorthand instead of mapping)."""
        yaml_text = """
metadata:
  protocol: Scalar Test
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp: 30 s
"""
        ast = parser.parse_string(yaml_text)
        step = ast.procedure[0].steps[0]
        assert isinstance(step, StepAST)
        assert step.technique == "ocp"
        assert step.parameters["value"] == "30 s"

    def test_multiple_steps_in_phase(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Multi Step
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 60 s
      - cv:
          between: 0.0 V and 1.0 V
          rate: 50 mV/s
          cycles: 3
      - eis:
          frequency: 100 kHz to 0.1 Hz
          amplitude: 10 mV
"""
        ast = parser.parse_string(yaml_text)
        assert len(ast.procedure[0].steps) == 3
        assert ast.procedure[0].steps[0].technique == "ocp"
        assert ast.procedure[0].steps[1].technique == "cv"
        assert ast.procedure[0].steps[2].technique == "eis"

    def test_metadata_version_coerced_to_string(self, parser: YAMLParser) -> None:
        """YAML may parse version '1.0' as a float; parser coerces to str."""
        yaml_text = """
metadata:
  protocol: Test
  version: 1.0
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        ast = parser.parse_string(yaml_text)
        assert isinstance(ast.metadata.version, str)
        assert ast.metadata.version == "1.0"

    def test_loop_count_as_integer(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Count Int
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - loop:
          count: 42
          steps:
            - ocp:
                for: 1 s
"""
        ast = parser.parse_string(yaml_text)
        loop = ast.procedure[0].steps[0]
        assert isinstance(loop, LoopAST)
        assert loop.count == 42
        assert isinstance(loop.count, int)

    def test_loop_missing_count_raises(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: No Count
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - loop:
          steps:
            - ocp:
                for: 1 s
"""
        with pytest.raises(MissingFieldError, match="count"):
            parser.parse_string(yaml_text)

    def test_loop_missing_steps_raises(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: No Steps
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - loop:
          count: 10
"""
        with pytest.raises(MissingFieldError, match="steps"):
            parser.parse_string(yaml_text)

    def test_safety_section_not_mapping_raises(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Safety Bad
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
safety: "not a dict"
"""
        with pytest.raises(YAMLStructureError, match="safety.*mapping"):
            parser.parse_string(yaml_text)

    def test_state_recovery_not_mapping_raises(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: SR Bad
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
state_recovery: "not a dict"
"""
        with pytest.raises(YAMLStructureError, match="state_recovery.*mapping"):
            parser.parse_string(yaml_text)

    def test_output_not_mapping_raises(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Out Bad
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
output: "not a dict"
"""
        with pytest.raises(YAMLStructureError, match="output.*mapping"):
            parser.parse_string(yaml_text)

    def test_stabilize_single_string(self, parser: YAMLParser) -> None:
        """stabilize can be a single string, auto-wrapped into list."""
        yaml_text = """
metadata:
  protocol: Stab String
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    stabilize: "OCP stable"
    steps:
      - ocp:
          for: 10 s
"""
        ast = parser.parse_string(yaml_text)
        phase = ast.procedure[0]
        assert phase.stabilize == ["OCP stable"]

    def test_metadata_additional_fields(self, parser: YAMLParser) -> None:
        """Extra metadata keys go into MetadataAST.additional."""
        yaml_text = """
metadata:
  protocol: Extra Fields
  version: "1.0"
  custom_field: value123
  lab: Building A
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        ast = parser.parse_string(yaml_text)
        assert ast.metadata.additional is not None
        assert ast.metadata.additional["custom_field"] == "value123"
        assert ast.metadata.additional["lab"] == "Building A"

    def test_electrolyte_object_additional_fields(self, parser: YAMLParser) -> None:
        yaml_text = """
metadata:
  protocol: Elyte Extra
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
  electrolyte:
    solute: H2SO4
    concentration_M: 0.5
    temperature: "25 C"
    degassed: true
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
"""
        ast = parser.parse_string(yaml_text)
        elyte = ast.system.electrolyte
        assert isinstance(elyte, ElectrolyteAST)
        assert elyte.additional is not None
        assert elyte.additional["temperature"] == "25 C"
        assert elyte.additional["degassed"] is True

    def test_safety_stop_if_single_string(self, parser: YAMLParser) -> None:
        """stop_if can be a single string, auto-wrapped into list."""
        yaml_text = """
metadata:
  protocol: Stop If String
  version: "1.0"
system:
  electrodes: 3
  reference: RHE
procedure:
  - name: P1
    steps:
      - ocp:
          for: 10 s
safety:
  stop_if: "current > 1 A"
"""
        ast = parser.parse_string(yaml_text)
        assert ast.safety.stop_if == ["current > 1 A"]
