"""Tests targeting uncovered lines in ecproc.parser.yaml_parser.

Each test is annotated with the source lines / methods it exercises.
"""

from __future__ import annotations

import textwrap

import pytest

from ecproc.parser.errors import (
    InvalidSyntaxError,
    UnknownTechniqueError,
    YAMLStructureError,
)
from ecproc.parser.yaml_parser import (
    YAMLParser,
    _LineLoader,
    _scalar_constructor,
    _sequence_constructor,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_HEADER = textwrap.dedent("""\
    metadata:
      protocol: Test
      version: "1.0"
    system:
      electrodes: 3
      reference: RHE
""")


def _yaml(body: str) -> str:
    """Combine the minimal header with a test-specific body."""
    return _MINIMAL_HEADER + textwrap.dedent(body)


def _parse(yaml_text: str):
    """Shortcut for parsing a YAML string."""
    return YAMLParser().parse_string(yaml_text)


# ===================================================================
# Lines 113-114, 118: _sequence_constructor & _scalar_constructor
# These are YAML constructors invoked automatically when parsing
# sequences and scalars. Parsing any file with lists/scalars hits them.
# ===================================================================


class TestYAMLConstructors:
    """Ensure that lists and plain scalars in YAML go through the custom constructors."""

    def test_scalar_and_sequence_constructors(self):
        """Parse a YAML with plain scalars and sequences (lines 113-114, 118)."""
        ast = _parse(_yaml("""\
            procedure:
              - name: Phase1
                steps:
                  - cv:
                      vertex1: 0.05 V
                      vertex2: 1.2 V
                      rate: 50 mV/s
                      cycles: 20
        """))
        assert len(ast.procedure) == 1
        assert ast.procedure[0].name == "Phase1"

    def test_sequence_constructor_directly(self):
        """Call _sequence_constructor directly to cover lines 113-114."""

        loader = _LineLoader("- 1\n- 2\n- 3\n")
        node = loader.get_single_node()
        result = _sequence_constructor(loader, node)
        assert result == [1, 2, 3]

    def test_scalar_constructor_directly(self):
        """Call _scalar_constructor directly to cover line 118."""

        loader = _LineLoader("hello\n")
        node = loader.get_single_node()
        result = _scalar_constructor(loader, node)
        assert result == "hello"


# ===================================================================
# Line 307: _parse_working_electrode when raw is not a dict
# ===================================================================


class TestWorkingElectrodeNotDict:
    def test_working_must_be_mapping(self):
        """system.working as a plain string triggers YAMLStructureError (line 307)."""
        with pytest.raises(YAMLStructureError, match="system.working.*must be a mapping"):
            _parse(_yaml("""\
                system:
                  electrodes: 3
                  reference: RHE
                  working: "not a dict"
                procedure:
                  - name: P
                    steps:
                      - ocp: 30 s
            """).replace(
                # Remove the duplicate system block from the header
                "system:\n  electrodes: 3\n  reference: RHE\n",
                "",
                1,
            ))

    def test_working_must_be_mapping_direct(self):
        """Simpler: system.working as a string (line 307)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
              working: "not a dict"
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
        """)
        with pytest.raises(YAMLStructureError, match="must be a mapping"):
            _parse(yaml_text)


# ===================================================================
# Line 346: _parse_electrolyte fallback to str(raw) for non-dict/str/None
# ===================================================================


class TestElectrolyteFallback:
    def test_electrolyte_as_int(self):
        """electrolyte: 42 falls back to str(42) (line 346)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
              electrolyte: 42
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
        """)
        ast = _parse(yaml_text)
        assert ast.system.electrolyte == "42"


# ===================================================================
# Line 372: _parse_phase when phase item is not a dict
# ===================================================================


class TestPhaseNotDict:
    def test_phase_must_be_mapping(self):
        """procedure item as a string triggers error (line 372)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - "not a dict"
        """)
        with pytest.raises(YAMLStructureError, match="Each phase must be a mapping"):
            _parse(yaml_text)


# ===================================================================
# Line 386: _parse_phase stabilize not string or list
# ===================================================================


class TestStabilizeNotStringOrList:
    def test_stabilize_must_be_string_or_list(self):
        """stabilize: 42 triggers error (line 386)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: X
                stabilize: 42
                steps:
                  - ocp: 30 s
        """)
        with pytest.raises(YAMLStructureError, match="stabilize.*must be a string or list"):
            _parse(yaml_text)


# ===================================================================
# Line 395: _parse_phase steps not a sequence
# ===================================================================


class TestStepsNotSequence:
    def test_steps_must_be_sequence(self):
        """steps: 'not a list' triggers error (line 395)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: X
                steps: "not a list"
        """)
        with pytest.raises(YAMLStructureError, match="steps.*must be a sequence"):
            _parse(yaml_text)


# ===================================================================
# Line 418: _parse_phase_block scalar fallback / Unknown technique
# ===================================================================


class TestUnknownTechnique:
    def test_unknown_technique_raises(self):
        """A bogus technique name triggers UnknownTechniqueError (line 418)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - bogus_technique:
                      param1: value1
        """)
        with pytest.raises(UnknownTechniqueError, match="bogus_technique"):
            _parse(yaml_text)

    def test_phase_block_scalar_fallback(self):
        """setup as a plain scalar goes through _parse_phase_block fallback (line 418)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                setup: "purge N2 30 min"
                steps:
                  - ocp: 30 s
        """)
        ast = _parse(yaml_text)
        assert ast.procedure[0].setup == {"value": "purge N2 30 min"}

    def test_cannot_determine_technique_multiple_keys(self):
        """Step with multiple unknown non-meta keys triggers Cannot determine (line 456)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - foo: 1
                    bar: 2
        """)
        with pytest.raises(YAMLStructureError, match="Cannot determine technique"):
            _parse(yaml_text)


# ===================================================================
# Line 427: _parse_step_or_loop when raw is not a dict
# ===================================================================


class TestStepOrLoopNotDict:
    def test_step_not_a_mapping(self):
        """A step item that is not a dict triggers 'Each step must be a mapping' (line 427)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - "just a string"
        """)
        with pytest.raises(YAMLStructureError, match="Each step must be a mapping"):
            _parse(yaml_text)


# ===================================================================
# Line 517: _parse_loop when loop value is not a dict
# ===================================================================


class TestLoopValueNotDict:
    def test_loop_value_must_be_mapping(self):
        """loop: 'not a dict' triggers error (line 517)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop: "not a dict"
        """)
        with pytest.raises(YAMLStructureError, match="loop.*must be a mapping"):
            _parse(yaml_text)


# ===================================================================
# Line 565: _parse_checkpoint when raw is not a dict
# ===================================================================


class TestCheckpointNotDict:
    def test_checkpoint_must_be_mapping(self):
        """checkpoint: 'bad' triggers error (line 565)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 5
                      steps:
                        - ocp: 30 s
                      checkpoint: "not a dict"
        """)
        with pytest.raises(YAMLStructureError, match="checkpoint.*must be a mapping"):
            _parse(yaml_text)


# ===================================================================
# Line 667: _parse_single_trigger single-key shorthand non-every key
# ===================================================================


class TestTriggerSingleKeyNonEvery:
    def test_single_key_trigger_non_every(self):
        """Single-key dict trigger where key does not start with 'every' (line 667)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        trigger:
                          custom_condition: "some value"
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert cp is not None
        assert len(cp.triggers) >= 1
        assert cp.triggers[0].type == "custom_condition"
        assert cp.triggers[0].value == "some value"


# ===================================================================
# vendor_flags extraction in _parse_step
# ===================================================================


class TestVendorFlags:
    def test_step_with_vendor_flags(self):
        """Step with vendor_flags mapping (line 427)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - cv:
                      vertex1: 0.05 V
                      vertex2: 1.2 V
                      rate: 50 mV/s
                      cycles: 20
                    vendor_flags:
                      biologic:
                        bandwidth: 5
        """)
        ast = _parse(yaml_text)
        step = ast.procedure[0].steps[0]
        assert step.vendor_flags is not None
        assert "biologic" in step.vendor_flags
        assert step.vendor_flags["biologic"]["bandwidth"] == 5


# ===================================================================
# Lines 456, 477-478: extract handling — string and dict forms
# ===================================================================


class TestExtract:
    def test_extract_as_string(self):
        """extract: 'my_var' stores a string (line 456)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - cv:
                      vertex1: 0.05 V
                      vertex2: 1.2 V
                      rate: 50 mV/s
                      cycles: 20
                    extract: my_var
        """)
        ast = _parse(yaml_text)
        step = ast.procedure[0].steps[0]
        assert step.extract == "my_var"

    def test_extract_as_dict(self):
        """extract: {name: x, type: y} stores a dict (lines 477-478)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - cv:
                      vertex1: 0.05 V
                      vertex2: 1.2 V
                      rate: 50 mV/s
                      cycles: 20
                    extract:
                      name: x
                      type: y
        """)
        ast = _parse(yaml_text)
        step = ast.procedure[0].steps[0]
        assert isinstance(step.extract, dict)
        assert step.extract["name"] == "x"
        assert step.extract["type"] == "y"

    def test_flat_step_extra_params(self):
        """Flat step form where extra top-level keys merge into parameters (lines 477-478)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - cv:
                      vertex1: 0.05 V
                    vertex2: 1.2 V
                    rate: 50 mV/s
                    cycles: 20
        """)
        ast = _parse(yaml_text)
        step = ast.procedure[0].steps[0]
        # vertex2, rate, cycles should be collected as top-level params
        assert "vertex2" in step.parameters
        assert "rate" in step.parameters


# ===================================================================
# Line 517: _parse_loop count as variable ${var}
# ===================================================================


class TestLoopVariableCount:
    def test_loop_count_variable(self):
        """loop count as ${n} is kept as-is string (line 517)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: "${n}"
                      steps:
                        - ocp: 30 s
        """)
        ast = _parse(yaml_text)
        loop = ast.procedure[0].steps[0]
        assert loop.count == "${n}"


# ===================================================================
# Lines 529-532: _parse_loop count fallback to str when not int-parsable
# ===================================================================


class TestLoopCountFallback:
    def test_loop_count_non_numeric_string(self):
        """loop count: 'abc' falls back to str (lines 529-532)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: "abc"
                      steps:
                        - ocp: 30 s
        """)
        ast = _parse(yaml_text)
        loop = ast.procedure[0].steps[0]
        assert loop.count == "abc"


# ===================================================================
# Line 536: _parse_loop when loop.steps is not a list
# ===================================================================


class TestLoopStepsNotList:
    def test_loop_steps_must_be_sequence(self):
        """loop.steps: 'not_a_list' triggers error (line 536)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 5
                      steps: "not_a_list"
        """)
        with pytest.raises(YAMLStructureError, match="loop.steps.*must be a sequence"):
            _parse(yaml_text)


# ===================================================================
# Line 565: _parse_loop stop_if field
# ===================================================================


class TestLoopStopIf:
    def test_loop_with_stop_if(self):
        """loop with stop_if is parsed (line 565)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 5
                      steps:
                        - ocp: 30 s
                      stop_if: "ecsa < 50%"
        """)
        ast = _parse(yaml_text)
        loop = ast.procedure[0].steps[0]
        assert loop.stop_if == "ecsa < 50%"


# ===================================================================
# Lines 581-583: _parse_checkpoint inline triggers fallback
# ===================================================================


class TestCheckpointInlineTriggers:
    def test_checkpoint_without_trigger_key_uses_inline(self):
        """Checkpoint with every_cycles but no trigger key (lines 581-583)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 1000
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        every_cycles: 100
                        do:
                          - cv:
                              vertex1: 0.05 V
                              vertex2: 1.2 V
                              rate: 50 mV/s
                              cycles: 3
        """)
        ast = _parse(yaml_text)
        loop = ast.procedure[0].steps[0]
        cp = loop.checkpoint
        assert cp is not None
        assert len(cp.triggers) >= 1
        assert cp.triggers[0].type == "every_cycles"
        assert cp.triggers[0].value == 100


# ===================================================================
# Lines 593-594: _parse_checkpoint do_raw as dict
# ===================================================================


class TestCheckpointDoAsDict:
    def test_checkpoint_do_as_single_dict(self):
        """checkpoint do: {technique: cv} as a dict not list (lines 593-594)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        trigger:
                          every: 5 cycles
                        do:
                          cv:
                            vertex1: 0.05 V
                            vertex2: 1.2 V
                            rate: 50 mV/s
                            cycles: 3
        """)
        ast = _parse(yaml_text)
        loop = ast.procedure[0].steps[0]
        cp = loop.checkpoint
        assert cp is not None
        assert len(cp.do) == 1
        assert cp.do[0].technique == "cv"


# ===================================================================
# Lines 636-639: _parse_triggers when raw is a list or a plain value
# ===================================================================


class TestParseTriggers:
    def test_triggers_as_list(self):
        """triggers: [{every: 5 h}] as a list (line 636)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        triggers:
                          - every: 5 h
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert cp is not None
        assert len(cp.triggers) >= 1

    def test_triggers_as_plain_string(self):
        """triggers: 'every 24 h' as a plain string value (line 639)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        trigger: "every 24 h"
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert cp is not None
        assert len(cp.triggers) >= 1
        assert cp.triggers[0].type == "every_time"


# ===================================================================
# Lines 655-673: _parse_single_trigger variations
# ===================================================================


class TestParseSingleTrigger:
    def test_trigger_when_key(self):
        """trigger dict with 'when' key (lines 655-660)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        trigger:
                          when: "ecsa < 50%"
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert cp is not None
        assert any(t.type == "when" for t in cp.triggers)

    def test_trigger_single_key_shorthand(self):
        """Single-key dict shorthand like {every_time: 24} (lines 662-667)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        trigger:
                          every_time: 24
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert cp is not None
        assert len(cp.triggers) >= 1

    def test_trigger_plain_string(self):
        """Plain string trigger 'every 5000 cycles' (lines 670-671)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        triggers:
                          - "every 5000 cycles"
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert cp is not None
        assert any(t.type == "every_cycles" for t in cp.triggers)

    def test_trigger_unparsable_raises(self):
        """Trigger that is neither dict nor string raises error (lines 673-676)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        triggers:
                          - 42
                        do:
                          - ocp: 10 s
        """)
        with pytest.raises(InvalidSyntaxError, match="Cannot parse trigger"):
            _parse(yaml_text)


# ===================================================================
# Lines 681, 685, 707: _parse_every_trigger — int, float, fallback text
# ===================================================================


class TestParseEveryTrigger:
    def test_every_trigger_int(self):
        """every: 100 (int) → every_cycles (line 681)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        trigger:
                          every: 100
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert cp is not None
        assert cp.triggers[0].type == "every_cycles"
        assert cp.triggers[0].value == 100

    def test_every_trigger_float(self):
        """every: 100.0 (float) → every_cycles (line 685)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        trigger:
                          every: 100.0
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert cp is not None
        # float should be coerced to int 100 via the float branch
        assert cp.triggers[0].type == "every_cycles"

    def test_every_trigger_fallback_text(self):
        """every: 'something_unusual' → fallback (line 707)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        trigger:
                          every: "something_unusual"
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert cp is not None
        assert cp.triggers[0].type == "every_time"
        assert cp.triggers[0].value == "something_unusual"


# ===================================================================
# Lines 711-723: _parse_trigger_string various string triggers
# ===================================================================


class TestParseTriggerString:
    def test_every_cycles_string(self):
        """'every 5000 cycles' → every_cycles (line 711-716)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        triggers:
                          - "every 5000 cycles"
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        t = cp.triggers[0]
        assert t.type == "every_cycles"
        assert t.value == 5000

    def test_every_time_string(self):
        """'every 24 h' → every_time (line 718)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        triggers:
                          - "every 24 h"
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        t = cp.triggers[0]
        assert t.type == "every_time"
        assert t.value == 24

    def test_when_string_trigger(self):
        """'when ecsa < 50%' → when (line 719-720)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        triggers:
                          - "when ecsa < 50%"
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        t = cp.triggers[0]
        assert t.type == "when"
        assert "ecsa" in t.value

    def test_arbitrary_text_trigger(self):
        """'some arbitrary text' → when fallback (line 722)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        triggers:
                          - "some arbitrary text"
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        t = cp.triggers[0]
        assert t.type == "when"
        assert t.value == "some arbitrary text"


# ===================================================================
# Lines 727-747: _extract_inline_triggers — every_cycles, every_time,
#                 every, when
# ===================================================================


class TestExtractInlineTriggers:
    def test_inline_every_cycles(self):
        """every_cycles key inline in checkpoint (line 736-740)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        every_cycles: 100
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert any(t.type == "every_cycles" for t in cp.triggers)

    def test_inline_every_time(self):
        """every_time key inline in checkpoint (line 742-744)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        every_time: 24
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert any(t.type == "every_time" for t in cp.triggers)

    def test_inline_every(self):
        """every key inline in checkpoint (line 730-731)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        every: 50 cycles
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert len(cp.triggers) >= 1

    def test_inline_when(self):
        """when key inline in checkpoint (line 733-735)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        when: "ecsa < 50%"
                        do:
                          - ocp: 10 s
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert any(t.type == "when" for t in cp.triggers)


# ===================================================================
# Line 754: _parse_checkpoint_action when raw is not dict
# ===================================================================


class TestCheckpointActionNotDict:
    def test_checkpoint_action_must_be_mapping(self):
        """checkpoint do item as string triggers error (line 754)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        trigger:
                          every: 5 cycles
                        do:
                          - "not a dict"
        """)
        with pytest.raises(YAMLStructureError, match="Checkpoint.*do.*must be mappings"):
            _parse(yaml_text)


# ===================================================================
# Line 760: _parse_checkpoint_action when raw has "name" key → phase
# ===================================================================


class TestCheckpointActionAsPhase:
    def test_checkpoint_do_item_with_name_as_phase(self):
        """checkpoint do item with 'name' key is parsed as phase (line 760)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - loop:
                      count: 100
                      steps:
                        - ocp: 30 s
                      checkpoint:
                        trigger:
                          every: 5 cycles
                        do:
                          - name: CharacterizationPhase
                            steps:
                              - cv:
                                  vertex1: 0.05 V
                                  vertex2: 1.2 V
                                  rate: 50 mV/s
                                  cycles: 3
        """)
        ast = _parse(yaml_text)
        cp = ast.procedure[0].steps[0].checkpoint
        assert cp is not None
        assert len(cp.do) == 1
        action = cp.do[0]
        assert action.name == "CharacterizationPhase"


# ===================================================================
# Line 784: _parse_safety voltage_window not list
# ===================================================================


class TestSafetyVoltageWindowNotList:
    def test_voltage_window_scalar(self):
        """voltage_window as scalar wraps to list (line 784)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
            safety:
              voltage_window: "0.0 to 2.0 V"
        """)
        ast = _parse(yaml_text)
        assert ast.safety is not None
        assert ast.safety.voltage_window == ["0.0 to 2.0 V"]


# ===================================================================
# Line 790: _parse_safety temperature_limits not list
# ===================================================================


class TestSafetyTemperatureLimitsNotList:
    def test_temperature_limits_scalar(self):
        """temperature_limits as scalar wraps to list (line 790)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
            safety:
              temperature_limits: "25 to 80 C"
        """)
        ast = _parse(yaml_text)
        assert ast.safety is not None
        assert ast.safety.temperature_limits == ["25 to 80 C"]


# ===================================================================
# Line 818: _parse_thermal_runaway when raw is not dict
# ===================================================================


class TestThermalRunawayNotDict:
    def test_thermal_runaway_must_be_mapping(self):
        """thermal_runaway: 'bad' triggers error (line 818)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
            safety:
              thermal_runaway: "not a dict"
        """)
        with pytest.raises(YAMLStructureError, match="thermal_runaway.*must be a mapping"):
            _parse(yaml_text)


# ===================================================================
# Line 830: _parse_reference_monitor when raw is not dict
# ===================================================================


class TestReferenceMonitorNotDict:
    def test_reference_monitor_must_be_mapping(self):
        """reference_electrode_monitor: 'bad' triggers error (line 830)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
            safety:
              reference_electrode_monitor: "not a dict"
        """)
        with pytest.raises(
            YAMLStructureError,
            match="reference_electrode_monitor.*must be a mapping",
        ):
            _parse(yaml_text)


# ===================================================================
# Lines 873, 875: _parse_recovery_steps — None returns None, non-list
#                  is wrapped in list
# ===================================================================


class TestParseRecoverySteps:
    def test_recovery_steps_single_dict(self):
        """after_pause as single step dict (not a list) wraps in list (lines 873, 875)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
            state_recovery:
              after_pause:
                ocp: 30 s
        """)
        ast = _parse(yaml_text)
        assert ast.state_recovery is not None
        assert ast.state_recovery.after_pause is not None
        assert len(ast.state_recovery.after_pause) >= 1

    def test_recovery_steps_none(self):
        """state_recovery without after_pause returns None (line 873)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
            state_recovery:
              after_error: "cell_off"
        """)
        ast = _parse(yaml_text)
        assert ast.state_recovery is not None
        assert ast.state_recovery.after_pause is None


# ===================================================================
# Lines 882, 884, 892: _parse_recovery_steps_or_strings — non-list
#                        wrapping, numeric item str'd, single string
# ===================================================================


class TestParseRecoveryStepsOrStrings:
    def test_after_error_single_string(self):
        """after_error: 'cell_off' → wraps in list (line 882)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
            state_recovery:
              after_error: "cell_off"
        """)
        ast = _parse(yaml_text)
        assert ast.state_recovery is not None
        assert ast.state_recovery.after_error is not None
        assert "cell_off" in ast.state_recovery.after_error

    def test_after_error_numeric_item(self):
        """after_error: [42] → numeric item gets str(42) (line 892)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
            state_recovery:
              after_error:
                - 42
        """)
        ast = _parse(yaml_text)
        assert ast.state_recovery is not None
        assert ast.state_recovery.after_error is not None
        assert "42" in ast.state_recovery.after_error

    def test_after_error_mixed_items(self):
        """after_error with dict, string, and int items (lines 884-892)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
            state_recovery:
              after_error:
                - "cell_off"
                - ocp: 10 s
                - 99
        """)
        ast = _parse(yaml_text)
        ae = ast.state_recovery.after_error
        assert ae is not None
        assert len(ae) == 3
        assert ae[0] == "cell_off"
        # ae[1] should be a StepAST
        assert hasattr(ae[1], "technique")
        assert ae[2] == "99"


# ===================================================================
# Line 915: _parse_output ecdl as non-dict
# ===================================================================


class TestOutputEcdlNonDict:
    def test_output_ecdl_as_bool(self):
        """output: {ecdl: true} → wraps as {value: true} (line 915)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
            output:
              ecdl: true
        """)
        ast = _parse(yaml_text)
        assert ast.output is not None
        assert ast.output.ecdl is not None
        assert ast.output.ecdl == {"value": True}

    def test_output_ecdl_as_dict(self):
        """output: {ecdl: {version: 2}} → normal dict (verifies line 913 path)."""
        yaml_text = textwrap.dedent("""\
            metadata:
              protocol: Test
              version: "1.0"
            system:
              electrodes: 3
              reference: RHE
            procedure:
              - name: P
                steps:
                  - ocp: 30 s
            output:
              ecdl:
                version: 2
        """)
        ast = _parse(yaml_text)
        assert ast.output is not None
        assert ast.output.ecdl is not None
        assert ast.output.ecdl.get("version") == 2
