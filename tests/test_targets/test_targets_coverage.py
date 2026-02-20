"""Tests covering uncovered lines in targets/ modules for 100% coverage."""

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

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _meta(**overrides):
    defaults = dict(
        protocol="Test",
        version="1.0",
        created=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ecproc_version="0.1.0",
        source_hash="abc",
    )
    defaults.update(overrides)
    return IRMetadata(**defaults)


def _prov():
    return IRProvenance(source_hash="abc", parser_version="0.1.0")


def _system():
    return IRSystem(electrodes=3, reference="RHE")


def _make_ir_with_loop():
    """Build a FaradayIR that contains a loop, stabilize, setup (dict), and teardown (dict)."""
    return FaradayIR(
        faraday_version="1.0",
        metadata=_meta(),
        system=_system(),
        procedure=[
            IRPhase(
                name="P1",
                setup={"action": "purge N2"},
                stabilize=["wait 30s"],
                steps=[
                    IRLoop(
                        count=5,
                        steps=[
                            IRStep(
                                technique="cv",
                                vertex1=0.05,
                                vertex2=1.2,
                                scan_rate_V_s=0.05,
                                cycles=1,
                            )
                        ],
                    )
                ],
                teardown={"action": "cell off"},
            )
        ],
        provenance=_prov(),
    )


def _make_ir_with_nested_loop():
    """Build a FaradayIR that contains nested loops."""
    return FaradayIR(
        faraday_version="1.0",
        metadata=_meta(),
        system=_system(),
        procedure=[
            IRPhase(
                name="P1",
                setup={"action": "purge N2"},
                stabilize=["wait 10s"],
                steps=[
                    IRLoop(
                        count=3,
                        steps=[
                            IRLoop(
                                count=2,
                                steps=[
                                    IRStep(
                                        technique="cv",
                                        vertex1=0.0,
                                        vertex2=1.0,
                                        scan_rate_V_s=0.05,
                                        cycles=1,
                                    )
                                ],
                            )
                        ],
                    )
                ],
                teardown={"action": "cell off"},
            )
        ],
        provenance=_prov(),
    )


def _make_ir_dict_with_loop():
    """Return a raw dict (not a FaradayIR) for testing model_validate path."""
    ir = _make_ir_with_loop()
    return ir.model_dump()


# ===================================================================
# 1. manual/compiler.py lines 40-41, 59-63 -- IRLoop handling
# ===================================================================
class TestManualCompilerLoopHandling:
    def test_compile_ir_with_loop(self):
        from ecproc.targets.manual.compiler import compile_to_manual

        ir = _make_ir_with_loop()
        result = compile_to_manual(ir)
        assert result is not None
        assert result.target == "manual"
        # The output should be a list of sections
        sections = result.output
        assert isinstance(sections, list)
        assert len(sections) > 0
        # Find the phase section and check it has a loop step
        phase_sections = [s for s in sections if s["type"] == "phase"]
        assert len(phase_sections) == 1
        phase = phase_sections[0]
        loop_steps = [s for s in phase["steps"] if s.get("type") == "loop"]
        assert len(loop_steps) == 1
        assert loop_steps[0]["count"] == 5

    def test_compile_ir_with_nested_loop(self):
        from ecproc.targets.manual.compiler import compile_to_manual

        ir = _make_ir_with_nested_loop()
        result = compile_to_manual(ir)
        assert result is not None
        assert result.target == "manual"


# ===================================================================
# 2. manual/markdown.py lines 61-62, 66-68, 73-74
# ===================================================================
class TestManualMarkdownRendering:
    def test_render_with_stabilize_loop_and_teardown(self):
        from ecproc.targets.manual.compiler import compile_to_manual
        from ecproc.targets.manual.markdown import render_markdown

        ir = _make_ir_with_loop()
        compiled = compile_to_manual(ir)
        # render_markdown takes the sections list, not the CompilationResult
        md = render_markdown(compiled.output)
        assert isinstance(md, str)
        assert len(md) > 0
        md_lower = md.lower()
        # Should contain stabilize text
        assert "stabilize" in md_lower or "wait" in md_lower
        # Should contain loop
        assert "loop" in md_lower
        # Should contain teardown
        assert "teardown" in md_lower

    def test_render_with_nested_loop(self):
        from ecproc.targets.manual.compiler import compile_to_manual
        from ecproc.targets.manual.markdown import render_markdown

        ir = _make_ir_with_nested_loop()
        compiled = compile_to_manual(ir)
        md = render_markdown(compiled.output)
        assert isinstance(md, str)
        assert len(md) > 0


# ===================================================================
# 3. manual/__init__.py line 37 -- ManualTarget.compile with dict
# ===================================================================
class TestManualTargetCompileDict:
    def test_compile_with_dict_input(self):
        from ecproc.targets.manual import ManualTarget

        ir_dict = _make_ir_dict_with_loop()
        target = ManualTarget()
        result = target.compile(ir_dict)
        assert result is not None
        assert result.target == "manual"

    def test_compile_with_faraday_ir_instance(self):
        from ecproc.targets.manual import ManualTarget

        ir = _make_ir_with_loop()
        target = ManualTarget()
        result = target.compile(ir)
        assert result is not None
        assert result.target == "manual"


# ===================================================================
# 4. python/__init__.py line 38 -- PythonTarget.compile with dict
# ===================================================================
class TestPythonTargetCompileDict:
    def test_compile_with_dict_input(self):
        from ecproc.targets.python import PythonTarget

        ir_dict = _make_ir_dict_with_loop()
        target = PythonTarget()
        result = target.compile(ir_dict)
        assert result is not None
        assert result.target == "python"

    def test_compile_with_faraday_ir_instance(self):
        from ecproc.targets.python import PythonTarget

        ir = _make_ir_with_loop()
        target = PythonTarget()
        result = target.compile(ir)
        assert result is not None
        assert result.target == "python"


# ===================================================================
# 5. python/compiler.py lines 53-54 -- nested IRLoop -> recursive call
# ===================================================================
class TestPythonCompilerNestedLoop:
    def test_compile_nested_loops(self):
        from ecproc.targets.python.compiler import compile_to_python

        ir = _make_ir_with_nested_loop()
        result = compile_to_python(ir)
        assert result is not None
        assert result.target == "python"
        # The output should contain a nested loop instruction
        instructions = result.output
        loop_insts = [i for i in instructions if i["type"] == "loop"]
        assert len(loop_insts) == 1
        # The outer loop should contain a nested loop step
        inner_steps = loop_insts[0]["steps"]
        inner_loops = [s for s in inner_steps if s["type"] == "loop"]
        assert len(inner_loops) == 1

    def test_compile_single_loop(self):
        from ecproc.targets.python.compiler import compile_to_python

        ir = _make_ir_with_loop()
        result = compile_to_python(ir)
        assert result is not None
        assert result.target == "python"


# ===================================================================
# 6. python/runtime.py lines 65-66 -- "stabilize" instruction handling
# ===================================================================
class TestPythonRuntimeStabilize:
    def test_execute_with_stabilize_instruction(self):
        from ecproc.targets.python.compiler import compile_to_python
        from ecproc.targets.python.hardware.mock import MockHardware
        from ecproc.targets.python.runtime import PythonRuntime

        ir = _make_ir_with_loop()
        compilation = compile_to_python(ir)
        # Verify that a stabilize instruction is in the output
        stab_insts = [i for i in compilation.output if i["type"] == "stabilize"]
        assert len(stab_insts) >= 1

        hardware = MockHardware()
        runtime = PythonRuntime(hardware=hardware)
        exec_result = runtime.execute(compilation.output)
        assert exec_result is not None
        assert exec_result.success is True

    def test_execute_nested_loop_with_stabilize(self):
        from ecproc.targets.python.compiler import compile_to_python
        from ecproc.targets.python.hardware.mock import MockHardware
        from ecproc.targets.python.runtime import PythonRuntime

        ir = _make_ir_with_nested_loop()
        compilation = compile_to_python(ir)

        hardware = MockHardware()
        runtime = PythonRuntime(hardware=hardware)
        exec_result = runtime.execute(compilation.output)
        assert exec_result is not None
        assert exec_result.success is True


# ===================================================================
# Additional edge cases for completeness
# ===================================================================
class TestManualCompilerEdgeCases:
    """Extra tests for manual compiler to ensure loop instructions are fully covered."""

    def test_loop_with_multiple_steps(self):
        from ecproc.targets.manual.compiler import compile_to_manual

        ir = FaradayIR(
            faraday_version="1.0",
            metadata=_meta(),
            system=_system(),
            procedure=[
                IRPhase(
                    name="MultiStep",
                    setup={"action": "rinse electrodes"},
                    stabilize=["equilibrate 60s"],
                    steps=[
                        IRLoop(
                            count=3,
                            steps=[
                                IRStep(
                                    technique="cv", vertex1=0.0, vertex2=1.0, scan_rate_V_s=0.05,
                                ),
                                IRStep(
                                    technique="eis", f_start=100000,
                                    f_end=0.1, amplitude=0.01, ppd=10,
                                ),
                            ],
                        ),
                    ],
                    teardown={"action": "disconnect cell"},
                )
            ],
            provenance=_prov(),
        )
        result = compile_to_manual(ir)
        assert result is not None
        assert result.target == "manual"

    def test_phase_without_optional_fields(self):
        """Phase with loop but no setup/stabilize/teardown."""
        from ecproc.targets.manual.compiler import compile_to_manual

        ir = FaradayIR(
            faraday_version="1.0",
            metadata=_meta(),
            system=_system(),
            procedure=[
                IRPhase(
                    name="Bare",
                    steps=[
                        IRLoop(
                            count=2,
                            steps=[
                                IRStep(technique="galvanostatic", current=0.001),
                            ],
                        ),
                    ],
                )
            ],
            provenance=_prov(),
        )
        result = compile_to_manual(ir)
        assert result is not None
        assert result.target == "manual"


class TestMarkdownRenderingEdgeCases:
    """Additional tests to guarantee stabilize, loop, and teardown lines are hit."""

    def test_render_phase_with_all_optional_fields(self):
        from ecproc.targets.manual.compiler import compile_to_manual
        from ecproc.targets.manual.markdown import render_markdown

        ir = FaradayIR(
            faraday_version="1.0",
            metadata=_meta(),
            system=_system(),
            procedure=[
                IRPhase(
                    name="FullPhase",
                    setup={"action": "purge Ar"},
                    stabilize=["wait 60s", "equilibrate OCV"],
                    steps=[
                        IRStep(technique="cv", vertex1=0.0, vertex2=0.8, scan_rate_V_s=0.01),
                        IRLoop(
                            count=10,
                            steps=[
                                IRStep(technique="galvanostatic", current=0.005),
                            ],
                        ),
                    ],
                    teardown={"action": "vent cell"},
                ),
            ],
            provenance=_prov(),
        )
        compiled = compile_to_manual(ir)
        md = render_markdown(compiled.output)
        assert isinstance(md, str)
        assert len(md) > 50  # Should have substantial content
        # Verify key sections appear
        assert "Setup" in md or "setup" in md.lower()
        assert "Loop" in md or "loop" in md.lower()
        assert "Teardown" in md or "teardown" in md.lower()

    def test_render_phase_without_optional_fields(self):
        from ecproc.targets.manual.compiler import compile_to_manual
        from ecproc.targets.manual.markdown import render_markdown

        ir = FaradayIR(
            faraday_version="1.0",
            metadata=_meta(),
            system=_system(),
            procedure=[
                IRPhase(
                    name="Minimal",
                    steps=[
                        IRStep(technique="ocp"),
                    ],
                )
            ],
            provenance=_prov(),
        )
        compiled = compile_to_manual(ir)
        md = render_markdown(compiled.output)
        assert isinstance(md, str)
        # Should NOT have stabilize or teardown sections
        assert "Stabilize" not in md
        assert "Teardown" not in md
