"""Tests for ecproc.targets.manual - markdown generation."""

from __future__ import annotations

from datetime import datetime, timezone

from ecproc.ir.schema import (
    FaradayIR,
    IRMetadata,
    IRPhase,
    IRProvenance,
    IRSafety,
    IRStep,
    IRSystem,
)
from ecproc.targets.base import CompilationResult
from ecproc.targets.manual.compiler import compile_to_manual
from ecproc.targets.manual.markdown import render_markdown


def _make_ir_with_safety() -> FaradayIR:
    """Create a FaradayIR with safety constraints for manual rendering."""
    return FaradayIR(
        metadata=IRMetadata(
            protocol="OER Stability",
            version="1.0",
            created=datetime.now(timezone.utc),
            ecproc_version="0.1.0",
            source_hash="sha256:abc123",
        ),
        system=IRSystem(
            electrodes=3,
            reference="RHE",
            counter="Pt wire",
        ),
        procedure=[
            IRPhase(
                name="Conditioning",
                setup={"gas": "N2"},
                steps=[
                    IRStep(technique="cv", vertex1=0.05, vertex2=1.2, rate=0.05, cycles=50),
                ],
            ),
            IRPhase(
                name="Measurement",
                steps=[
                    IRStep(
                        technique="eis",
                        f_start=100000,
                        f_end=0.1,
                        amplitude=0.01,
                        tag="baseline_eis",
                    ),
                ],
            ),
        ],
        safety=IRSafety(
            max_current_A=0.5,
            voltage_window_V=(-0.5, 2.0),
            temperature_limits_C=(15, 40),
        ),
        provenance=IRProvenance(
            source_hash="sha256:abc123",
            parser_version="0.1.0",
        ),
    )


class TestRenderMarkdown:
    """Test render_markdown() function."""

    def test_renders_title(self):
        md = render_markdown([], title="My Procedure")
        assert "# My Procedure" in md

    def test_renders_equipment_section(self):
        sections = [
            {
                "type": "equipment",
                "system": {"electrodes": 3, "reference": "RHE", "counter": "Pt wire"},
            }
        ]
        md = render_markdown(sections, title="Test")
        assert "## Equipment" in md
        assert "3-electrode" in md
        assert "RHE" in md
        assert "Pt wire" in md

    def test_renders_safety_section(self):
        sections = [
            {
                "type": "safety",
                "constraints": {
                    "max_current_A": 0.5,
                    "voltage_window_V": (-0.5, 2.0),
                    "temperature_limits_C": (15, 40),
                },
            }
        ]
        md = render_markdown(sections, title="Test")
        assert "## Safety Constraints" in md
        assert "WARNING" in md
        assert "0.5" in md

    def test_renders_phase_section(self):
        sections = [
            {
                "type": "phase",
                "name": "Conditioning",
                "setup": {"gas": "N2"},
                "stabilize": None,
                "steps": [
                    {
                        "technique": "cv",
                        "parameters": {"vertex1": 0.05, "vertex2": 1.2},
                        "tag": None,
                    },
                ],
                "teardown": None,
            }
        ]
        md = render_markdown(sections, title="Test")
        assert "## Phase: Conditioning" in md
        assert "CV" in md


class TestCompileToManual:
    """Test compile_to_manual() integration."""

    def test_returns_compilation_result(self):
        ir = _make_ir_with_safety()
        result = compile_to_manual(ir)
        assert isinstance(result, CompilationResult)
        assert result.target == "manual"

    def test_contains_equipment_section(self):
        ir = _make_ir_with_safety()
        result = compile_to_manual(ir)
        types = [s["type"] for s in result.output]
        assert "equipment" in types

    def test_contains_safety_section(self):
        ir = _make_ir_with_safety()
        result = compile_to_manual(ir)
        types = [s["type"] for s in result.output]
        assert "safety" in types

    def test_contains_phase_sections(self):
        ir = _make_ir_with_safety()
        result = compile_to_manual(ir)
        phase_sections = [s for s in result.output if s["type"] == "phase"]
        assert len(phase_sections) == 2
        assert phase_sections[0]["name"] == "Conditioning"
        assert phase_sections[1]["name"] == "Measurement"

    def test_full_markdown_render(self):
        ir = _make_ir_with_safety()
        result = compile_to_manual(ir)
        md = render_markdown(result.output, title=ir.metadata.protocol)
        assert "# OER Stability" in md
        assert "## Equipment" in md
        assert "## Safety Constraints" in md
        assert "## Phase: Conditioning" in md
        assert "## Phase: Measurement" in md
