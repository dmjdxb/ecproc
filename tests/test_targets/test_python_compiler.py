"""Tests for ecproc.targets.python.compiler - IR to Python compilation."""

from __future__ import annotations

from datetime import datetime, timezone

from ecproc.ir.schema import (
    FaradayIR,
    IRLoop,
    IRMetadata,
    IRPhase,
    IRProvenance,
    IRStep,
    IRSystem,
)
from ecproc.targets.base import CompilationResult
from ecproc.targets.python.compiler import compile_to_python


def _make_minimal_ir(phases: list[IRPhase] | None = None) -> FaradayIR:
    """Create a minimal FaradayIR for testing."""
    if phases is None:
        phases = [
            IRPhase(
                name="Test Phase",
                steps=[
                    IRStep(
                        technique="cv",
                        vertex1=0.05,
                        vertex2=1.2,
                        rate=0.05,
                        cycles=3,
                    )
                ],
            )
        ]
    return FaradayIR(
        metadata=IRMetadata(
            protocol="Test",
            version="1.0",
            created=datetime.now(timezone.utc),
            ecproc_version="0.1.0",
            source_hash="sha256:abc123",
        ),
        system=IRSystem(electrodes=3, reference="RHE"),
        procedure=phases,
        provenance=IRProvenance(
            source_hash="sha256:abc123",
            parser_version="0.1.0",
        ),
    )


class TestCompileToPython:
    """Test compile_to_python() function."""

    def test_returns_compilation_result(self):
        ir = _make_minimal_ir()
        result = compile_to_python(ir)
        assert isinstance(result, CompilationResult)

    def test_target_is_python(self):
        ir = _make_minimal_ir()
        result = compile_to_python(ir)
        assert result.target == "python"

    def test_output_is_list_of_instructions(self):
        ir = _make_minimal_ir()
        result = compile_to_python(ir)
        assert isinstance(result.output, list)
        assert len(result.output) > 0

    def test_single_phase_produces_start_and_end(self):
        ir = _make_minimal_ir()
        result = compile_to_python(ir)
        instructions = result.output
        types = [inst["type"] for inst in instructions]
        assert "phase_start" in types
        assert "phase_end" in types

    def test_step_instruction_has_technique(self):
        ir = _make_minimal_ir()
        result = compile_to_python(ir)
        step_instructions = [i for i in result.output if i["type"] == "step"]
        assert len(step_instructions) >= 1
        assert step_instructions[0]["technique"] == "cv"

    def test_step_instruction_has_parameters(self):
        ir = _make_minimal_ir()
        result = compile_to_python(ir)
        step_instructions = [i for i in result.output if i["type"] == "step"]
        assert "parameters" in step_instructions[0]

    def test_multiple_phases_produce_correct_structure(self):
        phases = [
            IRPhase(
                name="Phase A",
                steps=[IRStep(technique="ocp")],
            ),
            IRPhase(
                name="Phase B",
                steps=[IRStep(technique="cv", vertex1=0.0, vertex2=1.0)],
            ),
        ]
        ir = _make_minimal_ir(phases=phases)
        result = compile_to_python(ir)
        phase_starts = [i for i in result.output if i["type"] == "phase_start"]
        assert len(phase_starts) == 2
        assert phase_starts[0]["name"] == "Phase A"
        assert phase_starts[1]["name"] == "Phase B"

    def test_loop_compiled_to_instruction(self):
        phases = [
            IRPhase(
                name="Loop Phase",
                steps=[
                    IRLoop(
                        count=100,
                        steps=[
                            IRStep(technique="cv", vertex1=0.05, vertex2=1.2),
                            IRStep(technique="eis", f_start=100000, f_end=0.1),
                        ],
                    )
                ],
            ),
        ]
        ir = _make_minimal_ir(phases=phases)
        result = compile_to_python(ir)
        loop_instructions = [i for i in result.output if i["type"] == "loop"]
        assert len(loop_instructions) == 1
        assert loop_instructions[0]["count"] == 100

    def test_stabilize_produces_instruction(self):
        phases = [
            IRPhase(
                name="Stabilize Phase",
                stabilize=["OCP stable < 1 mV/min"],
                steps=[IRStep(technique="ocp")],
            ),
        ]
        ir = _make_minimal_ir(phases=phases)
        result = compile_to_python(ir)
        stabilize = [i for i in result.output if i["type"] == "stabilize"]
        assert len(stabilize) == 1
        assert stabilize[0]["conditions"] == ["OCP stable < 1 mV/min"]

    def test_teardown_produces_instruction(self):
        phases = [
            IRPhase(
                name="Teardown Phase",
                steps=[IRStep(technique="ocp")],
                teardown={"gas": "off"},
            ),
        ]
        ir = _make_minimal_ir(phases=phases)
        result = compile_to_python(ir)
        teardown_insts = [i for i in result.output if i["type"] == "phase_teardown"]
        assert len(teardown_insts) == 1
        assert teardown_insts[0]["teardown"] == {"gas": "off"}
