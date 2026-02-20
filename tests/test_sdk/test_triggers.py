"""Tests for ecproc.sdk.triggers - trigger functions for checkpoints."""

from __future__ import annotations

from ecproc.parser.ast import TriggerAST
from ecproc.sdk.triggers import Trigger, all_of, any_of, every, when

# ---------------------------------------------------------------------------
# Trigger class
# ---------------------------------------------------------------------------


class TestTriggerClass:
    """Test the Trigger dataclass directly."""

    def test_trigger_creation(self):
        t = Trigger("every_cycles", 100, unit="cycles")
        assert t.type == "every_cycles"
        assert t.value == 100
        assert t.unit == "cycles"

    def test_trigger_to_ast(self):
        t = Trigger("every_cycles", 100, unit="cycles")
        ast = t.to_ast()
        assert isinstance(ast, TriggerAST)
        assert ast.type == "every_cycles"
        assert ast.value == 100
        assert ast.unit == "cycles"

    def test_trigger_without_unit(self):
        t = Trigger("when", "current < 0.001 A")
        assert t.unit is None
        ast = t.to_ast()
        assert ast.unit is None


# ---------------------------------------------------------------------------
# every() - periodic triggers
# ---------------------------------------------------------------------------


class TestEvery:
    """Test the every() trigger factory."""

    def test_every_with_cycles(self):
        t = every(5000, "cycles")
        assert isinstance(t, Trigger)
        assert t.type == "every_cycles"
        assert t.value == 5000
        assert t.unit == "cycles"

    def test_every_with_cycles_default_unit(self):
        t = every(100)
        assert t.type == "every_cycles"
        assert t.value == 100
        assert t.unit == "cycles"

    def test_every_with_time_minutes(self):
        t = every(30, "min")
        assert t.type == "every_time"
        assert t.value == 30
        assert t.unit == "min"

    def test_every_with_time_seconds(self):
        t = every(10, "s")
        assert t.type == "every_time"
        assert t.value == 10
        assert t.unit == "s"

    def test_every_with_time_hours(self):
        t = every(24, "h")
        assert t.type == "every_time"
        assert t.value == 24
        assert t.unit == "h"

    def test_every_converts_to_int_for_cycles(self):
        t = every(5000.0, "cycles")
        assert t.value == 5000
        assert isinstance(t.value, int)

    def test_every_to_ast(self):
        t = every(5000, "cycles")
        ast = t.to_ast()
        assert isinstance(ast, TriggerAST)
        assert ast.type == "every_cycles"
        assert ast.value == 5000


# ---------------------------------------------------------------------------
# when() - conditional triggers
# ---------------------------------------------------------------------------


class TestWhen:
    """Test the when() trigger factory."""

    def test_when_with_condition(self):
        t = when("current < 0.001 A")
        assert isinstance(t, Trigger)
        assert t.type == "when"
        assert t.value == "current < 0.001 A"

    def test_when_with_complex_condition(self):
        t = when("ECSA_loss > 20%")
        assert t.type == "when"
        assert t.value == "ECSA_loss > 20%"

    def test_when_to_ast(self):
        t = when("current < 0.001 A")
        ast = t.to_ast()
        assert ast.type == "when"
        assert ast.value == "current < 0.001 A"
        assert ast.unit is None


# ---------------------------------------------------------------------------
# any_of() - OR combination
# ---------------------------------------------------------------------------


class TestAnyOf:
    """Test the any_of() trigger combinator."""

    def test_any_of_combines_triggers(self):
        t1 = every(5000, "cycles")
        t2 = every(24, "h")
        result = any_of(t1, t2)
        assert isinstance(result, dict)
        assert result["logic"] == "any"
        assert len(result["triggers"]) == 2

    def test_any_of_produces_trigger_asts(self):
        t1 = every(100, "cycles")
        t2 = when("ECSA_loss > 10%")
        result = any_of(t1, t2)
        for trigger in result["triggers"]:
            assert isinstance(trigger, TriggerAST)

    def test_any_of_preserves_trigger_details(self):
        t1 = every(5000, "cycles")
        t2 = every(24, "h")
        result = any_of(t1, t2)
        assert result["triggers"][0].type == "every_cycles"
        assert result["triggers"][0].value == 5000
        assert result["triggers"][1].type == "every_time"
        assert result["triggers"][1].value == 24

    def test_any_of_single_trigger(self):
        t1 = every(100, "cycles")
        result = any_of(t1)
        assert result["logic"] == "any"
        assert len(result["triggers"]) == 1


# ---------------------------------------------------------------------------
# all_of() - AND combination
# ---------------------------------------------------------------------------


class TestAllOf:
    """Test the all_of() trigger combinator."""

    def test_all_of_combines_triggers(self):
        t1 = every(5000, "cycles")
        t2 = when("temperature > 30 C")
        result = all_of(t1, t2)
        assert isinstance(result, dict)
        assert result["logic"] == "all"
        assert len(result["triggers"]) == 2

    def test_all_of_produces_trigger_asts(self):
        t1 = every(100, "cycles")
        t2 = when("current < 0.001 A")
        result = all_of(t1, t2)
        for trigger in result["triggers"]:
            assert isinstance(trigger, TriggerAST)

    def test_all_of_preserves_trigger_details(self):
        t1 = every(5000, "cycles")
        t2 = when("ECSA_loss > 20%")
        result = all_of(t1, t2)
        assert result["triggers"][0].type == "every_cycles"
        assert result["triggers"][1].type == "when"
        assert result["triggers"][1].value == "ECSA_loss > 20%"


# ---------------------------------------------------------------------------
# Checkpoint integration via Phase.loop()
# ---------------------------------------------------------------------------


class TestCheckpointWithTriggers:
    """Test building checkpoints with triggers through the SDK Phase."""

    def test_loop_with_checkpoint_from_phase(self):
        """Verify loop + checkpoint construction through Phase API."""
        from ecproc.sdk.phase import Phase

        phase = Phase("Durability")
        lp = phase.loop(10000)
        lp.cv(vertex1=0.05, vertex2=1.2, rate=100, cycles=1)
        # Loop doesn't have direct checkpoint API in the current SDK,
        # but we can verify the loop itself
        ast = lp.to_ast()
        assert ast.count == 10000
        assert len(ast.steps) == 1
        assert ast.steps[0].technique == "cv"
