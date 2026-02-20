"""Tests for uncovered branches in ecproc.ir.generator."""


from ecproc.ir.generator import generate_ir
from ecproc.parser.ast import (
    CheckpointAST,
    LoopAST,
    MetadataAST,
    PhaseAST,
    ProcedureAST,
    ReferenceMonitorAST,
    SafetyAST,
    StateRecoveryAST,
    StepAST,
    SystemAST,
    TriggerAST,
)


def _minimal_procedure(**overrides):
    """Build a minimal valid ProcedureAST with optional overrides."""
    defaults = dict(
        metadata=MetadataAST(protocol="Test", version="1.0"),
        system=SystemAST(electrodes=3, reference="RHE"),
        procedure=[
            PhaseAST(
                name="P1",
                steps=[
                    StepAST(
                        technique="cv",
                        parameters={
                            "vertex1": "0.05 V",
                            "vertex2": "1.2 V",
                            "rate": "50 mV/s",
                            "cycles": 20,
                        },
                    )
                ],
            )
        ],
    )
    defaults.update(overrides)
    return ProcedureAST(**defaults)


# ---------------------------------------------------------------------------
# 1. _convert_checkpoint: PhaseAST item inside checkpoint.do (lines 160-161)
# ---------------------------------------------------------------------------


class TestCheckpointWithPhaseAST:
    """Cover the isinstance(item, PhaseAST) branch in _convert_checkpoint."""

    def test_checkpoint_do_contains_phase_ast(self):
        inner_phase = PhaseAST(
            name="RecoveryPhase",
            steps=[
                StepAST(
                    technique="ocp",
                    parameters={"duration": "30 s"},
                )
            ],
        )
        checkpoint = CheckpointAST(
            triggers=[TriggerAST(type="time", value=60, unit="s")],
            logic="any",
            reset="independent",
            do=[inner_phase],
        )
        loop = LoopAST(
            count=3,
            steps=[
                StepAST(
                    technique="cv",
                    parameters={
                        "vertex1": "0.05 V",
                        "vertex2": "1.2 V",
                        "rate": "50 mV/s",
                        "cycles": 5,
                    },
                )
            ],
            checkpoint=checkpoint,
        )
        phase = PhaseAST(name="LoopPhase", steps=[loop])
        ast = _minimal_procedure(procedure=[phase])

        ir = generate_ir(ast)

        assert ir is not None
        # The IR should have compiled without error and contain the phase
        assert len(ir.procedure) >= 1

    def test_checkpoint_do_contains_step_and_phase(self):
        """Checkpoint do list with both a StepAST and a PhaseAST."""
        inner_phase = PhaseAST(
            name="InnerPhase",
            steps=[
                StepAST(technique="ocp", parameters={"duration": "10 s"})
            ],
        )
        inner_step = StepAST(
            technique="eis",
            parameters={"start_freq": "100 kHz", "end_freq": "0.1 Hz"},
        )
        checkpoint = CheckpointAST(
            triggers=[TriggerAST(type="cycle", value=10, unit=None)],
            logic="any",
            reset="independent",
            do=[inner_step, inner_phase],
        )
        loop = LoopAST(
            count=2,
            steps=[
                StepAST(
                    technique="cv",
                    parameters={
                        "vertex1": "0.05 V",
                        "vertex2": "1.2 V",
                        "rate": "50 mV/s",
                        "cycles": 10,
                    },
                )
            ],
            checkpoint=checkpoint,
        )
        phase = PhaseAST(name="Mixed", steps=[loop])
        ast = _minimal_procedure(procedure=[phase])

        ir = generate_ir(ast)
        assert ir is not None


# ---------------------------------------------------------------------------
# 2. _convert_safety: ValueError pass branches (lines 207-208, 218-219,
#    227-228, 249-250)
# ---------------------------------------------------------------------------


class TestSafetyValueErrorBranches:
    """Cover ValueError catch-and-pass branches in _convert_safety."""

    def test_unparseable_max_current(self):
        """max_current with a value that parse_value_unit cannot handle."""
        safety = SafetyAST(max_current="bad_value")
        ast = _minimal_procedure(safety=safety)

        ir = generate_ir(ast)
        assert ir is not None
        # The safety block should exist but max_current_A should be None/skipped
        if ir.safety is not None:
            assert ir.safety.max_current_A is None

    def test_unparseable_voltage_window(self):
        """voltage_window items that parse_value_unit cannot handle."""
        safety = SafetyAST(voltage_window=["not_a_number", "also_bad"])
        ast = _minimal_procedure(safety=safety)

        ir = generate_ir(ast)
        assert ir is not None

    def test_unparseable_temperature_limits(self):
        """temperature_limits with bad values."""
        safety = SafetyAST(temperature_limits=["garbage_temp", "more_garbage"])
        ast = _minimal_procedure(safety=safety)

        ir = generate_ir(ast)
        assert ir is not None

    def test_unparseable_max_ocp_drift(self):
        """reference_electrode_monitor.max_ocp_drift with a bad value."""
        ref_monitor = ReferenceMonitorAST(
            max_ocp_drift="completely_invalid",
            action="pause",
        )
        safety = SafetyAST(reference_electrode_monitor=ref_monitor)
        ast = _minimal_procedure(safety=safety)

        ir = generate_ir(ast)
        assert ir is not None

    def test_all_unparseable_safety_values(self):
        """All safety fields have unparseable values simultaneously."""
        ref_monitor = ReferenceMonitorAST(
            max_Ru_change="1.5x",
            max_ocp_drift="bad_drift",
            action="stop",
        )
        safety = SafetyAST(
            max_current="bad_current",
            voltage_window=["bad_low", "bad_high"],
            temperature_limits=["bad_min", "bad_max"],
            reference_electrode_monitor=ref_monitor,
        )
        ast = _minimal_procedure(safety=safety)

        ir = generate_ir(ast)
        assert ir is not None

    def test_valid_safety_alongside_invalid(self):
        """Mix of valid and invalid safety values."""
        safety = SafetyAST(
            max_current="bad_value",
            voltage_window=["0.0 V", "bad_high"],
        )
        ast = _minimal_procedure(safety=safety)

        ir = generate_ir(ast)
        assert ir is not None


# ---------------------------------------------------------------------------
# 3. _convert_state_recovery (lines 267-280)
# ---------------------------------------------------------------------------


class TestStateRecovery:
    """Cover _convert_state_recovery with all three fields."""

    def test_state_recovery_all_fields(self):
        """after_pause, after_checkpoint, after_error all populated."""
        pause_steps = [
            StepAST(technique="ocp", parameters={"duration": "60 s"}),
        ]
        checkpoint_steps = [
            StepAST(technique="eis", parameters={"start_freq": "100 kHz", "end_freq": "0.1 Hz"}),
        ]
        error_steps = [
            StepAST(technique="ocp", parameters={"duration": "30 s"}),
            "abort",
        ]
        recovery = StateRecoveryAST(
            after_pause=pause_steps,
            after_checkpoint=checkpoint_steps,
            after_error=error_steps,
        )
        ast = _minimal_procedure(state_recovery=recovery)

        ir = generate_ir(ast)
        assert ir is not None
        assert ir.state_recovery is not None

    def test_state_recovery_after_pause_only(self):
        """Only after_pause is set."""
        recovery = StateRecoveryAST(
            after_pause=[
                StepAST(technique="ocp", parameters={"duration": "10 s"}),
            ],
        )
        ast = _minimal_procedure(state_recovery=recovery)

        ir = generate_ir(ast)
        assert ir is not None
        assert ir.state_recovery is not None

    def test_state_recovery_after_checkpoint_only(self):
        """Only after_checkpoint is set."""
        recovery = StateRecoveryAST(
            after_checkpoint=[
                StepAST(technique="cv", parameters={
                    "vertex1": "0.05 V",
                    "vertex2": "1.2 V",
                    "rate": "50 mV/s",
                    "cycles": 3,
                }),
            ],
        )
        ast = _minimal_procedure(state_recovery=recovery)

        ir = generate_ir(ast)
        assert ir is not None
        assert ir.state_recovery is not None

    def test_state_recovery_after_error_with_strings(self):
        """after_error containing string actions like 'abort'."""
        recovery = StateRecoveryAST(
            after_error=["abort"],
        )
        ast = _minimal_procedure(state_recovery=recovery)

        ir = generate_ir(ast)
        assert ir is not None
        assert ir.state_recovery is not None

    def test_state_recovery_after_error_mixed(self):
        """after_error with both StepAST and string items."""
        recovery = StateRecoveryAST(
            after_error=[
                StepAST(technique="ocp", parameters={"duration": "5 s"}),
                "retry",
                StepAST(technique="ocp", parameters={"duration": "10 s"}),
                "abort",
            ],
        )
        ast = _minimal_procedure(state_recovery=recovery)

        ir = generate_ir(ast)
        assert ir is not None
        assert ir.state_recovery is not None

    def test_state_recovery_empty_lists(self):
        """State recovery with empty lists for all fields."""
        recovery = StateRecoveryAST(
            after_pause=[],
            after_checkpoint=[],
            after_error=[],
        )
        ast = _minimal_procedure(state_recovery=recovery)

        ir = generate_ir(ast)
        assert ir is not None
