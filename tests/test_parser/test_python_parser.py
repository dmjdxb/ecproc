"""Tests for the Python SDK parser (PythonParser).

Verifies that SDK-built Procedure objects produce valid AST via
PythonParser.parse_procedure().
"""

from __future__ import annotations

import pytest

from ecproc.parser.ast import (
    LoopAST,
    ProcedureAST,
    StepAST,
)
from ecproc.parser.python_parser import PythonParser
from ecproc.sdk.procedure import Procedure


@pytest.fixture
def python_parser() -> PythonParser:
    """Return a fresh PythonParser instance."""
    return PythonParser()


class TestPythonParserBasic:
    """Basic PythonParser tests."""

    def test_parse_procedure_returns_ast(self, python_parser: PythonParser) -> None:
        """PythonParser.parse_procedure returns a ProcedureAST."""
        proc = Procedure("Test Protocol", version="1.0")
        proc.system(electrodes=3, reference="RHE")
        with proc.phase("Phase 1") as p:
            p.ocp(duration=60)
        ast = python_parser.parse_procedure(proc)
        assert isinstance(ast, ProcedureAST)

    def test_metadata_from_sdk(self, python_parser: PythonParser) -> None:
        """Metadata fields from Procedure constructor appear in AST."""
        proc = Procedure("My Experiment", version="2.0", author="Tester")
        proc.system(electrodes=3, reference="RHE")
        with proc.phase("P1") as p:
            p.ocp(duration=10)
        ast = python_parser.parse_procedure(proc)
        assert ast.metadata.protocol == "My Experiment"
        assert ast.metadata.version == "2.0"
        assert ast.metadata.author == "Tester"

    def test_system_config(self, python_parser: PythonParser) -> None:
        """System configuration flows through to AST."""
        proc = Procedure("Sys Test", version="1.0")
        proc.system(electrodes=2, reference="Ag/AgCl")
        with proc.phase("P1") as p:
            p.ocp(duration=10)
        ast = python_parser.parse_procedure(proc)
        assert ast.system.electrodes == 2
        assert ast.system.reference == "Ag/AgCl"

    def test_simple_cv_step(self, python_parser: PythonParser) -> None:
        """A simple CV step added via SDK appears in AST."""
        proc = Procedure("CV Test", version="1.0")
        proc.system(electrodes=3, reference="RHE")
        with proc.phase("Conditioning") as p:
            p.cv(vertex1=0.05, vertex2=1.2, rate=50, cycles=20)
        ast = python_parser.parse_procedure(proc)
        assert len(ast.procedure) == 1
        phase = ast.procedure[0]
        assert phase.name == "Conditioning"
        assert len(phase.steps) == 1
        step = phase.steps[0]
        assert isinstance(step, StepAST)
        assert step.technique == "cv"
        assert step.parameters["vertex1"] == 0.05
        assert step.parameters["vertex2"] == 1.2

    def test_multiple_phases(self, python_parser: PythonParser) -> None:
        """Multiple phases added via context managers appear in order."""
        proc = Procedure("Multi Phase", version="1.0")
        proc.system(electrodes=3, reference="RHE")
        with proc.phase("Phase A") as p:
            p.ocp(duration=60)
        with proc.phase("Phase B") as p:
            p.cv(vertex1=0.0, vertex2=1.0, rate=50, cycles=5)
        with proc.phase("Phase C") as p:
            p.eis(f_start=100000, f_end=0.1, amplitude=0.01)
        ast = python_parser.parse_procedure(proc)
        assert len(ast.procedure) == 3
        assert [p.name for p in ast.procedure] == ["Phase A", "Phase B", "Phase C"]

    def test_loop_in_phase(self, python_parser: PythonParser) -> None:
        """A loop created via SDK produces a LoopAST."""
        proc = Procedure("Loop Test", version="1.0")
        proc.system(electrodes=3, reference="RHE")
        with proc.phase("Durability") as p:
            loop = p.loop(1000)
            loop.cv(vertex1=0.6, vertex2=1.0, rate=100, cycles=1)
        ast = python_parser.parse_procedure(proc)
        phase = ast.procedure[0]
        assert len(phase.steps) == 1
        loop_ast = phase.steps[0]
        assert isinstance(loop_ast, LoopAST)
        assert loop_ast.count == 1000
        assert len(loop_ast.steps) == 1
        assert loop_ast.steps[0].technique == "cv"

    def test_default_system_created(self, python_parser: PythonParser) -> None:
        """If system() is never called, to_ast() uses defaults."""
        proc = Procedure("Default Sys", version="1.0")
        with proc.phase("P1") as p:
            p.ocp(duration=10)
        ast = python_parser.parse_procedure(proc)
        assert ast.system.electrodes == 3
        assert ast.system.reference == "RHE"

    def test_step_with_tag_and_extract(self, python_parser: PythonParser) -> None:
        """Tags and extract passed to SDK steps appear in AST."""
        proc = Procedure("Tag Test", version="1.0")
        proc.system(electrodes=3, reference="RHE")
        with proc.phase("P1") as p:
            p.eis(
                f_start=100000,
                f_end=0.1,
                amplitude=0.01,
                tag="ir_comp",
                extract="Ru",
            )
        ast = python_parser.parse_procedure(proc)
        step = ast.procedure[0].steps[0]
        assert isinstance(step, StepAST)
        assert step.tag == "ir_comp"
        assert step.extract == "Ru"

    def test_phase_setup_and_teardown(self, python_parser: PythonParser) -> None:
        """Phase setup/teardown set via SDK appear in AST."""
        proc = Procedure("Setup Teardown", version="1.0")
        proc.system(electrodes=3, reference="RHE")
        with proc.phase("P1") as p:
            p.setup(gas="N2", rotation=1600)
            p.ocp(duration=60)
            p.teardown(gas="off")
        ast = python_parser.parse_procedure(proc)
        phase = ast.procedure[0]
        assert phase.setup is not None
        assert phase.setup["gas"] == "N2"
        assert phase.setup["rotation"] == 1600
        assert phase.teardown is not None
        assert phase.teardown["gas"] == "off"
