"""Tests for ecproc.protocols - standard electrochemical protocols."""

from __future__ import annotations

import pytest

from ecproc.protocols.base import StandardProtocol
from ecproc.protocols.doe.catalyst_support_ast import DOECatalystSupportAST
from ecproc.protocols.doe.oer_catalyst_ast import DOEOERCatalystAST
from ecproc.protocols.doe.orr_catalyst_ast import DOEORRCatalystAST
from ecproc.protocols.jrc.alkaline_electrolysis import JRCAlkalineElectrolysis
from ecproc.protocols.jrc.pem_electrolysis import JRCPEMElectrolysis
from ecproc.sdk.procedure import Procedure

# ---------------------------------------------------------------------------
# Base StandardProtocol
# ---------------------------------------------------------------------------


class TestStandardProtocol:
    """Test the base StandardProtocol class."""

    def test_has_name_attribute(self):
        proto = StandardProtocol()
        assert hasattr(proto, "name")
        assert proto.name == ""

    def test_has_description_attribute(self):
        proto = StandardProtocol()
        assert hasattr(proto, "description")
        assert proto.description == ""

    def test_to_procedure_raises_not_implemented(self):
        proto = StandardProtocol()
        with pytest.raises(NotImplementedError):
            proto.to_procedure()

    def test_to_yaml_raises_not_implemented(self):
        proto = StandardProtocol()
        with pytest.raises(NotImplementedError):
            proto.to_yaml()


# ---------------------------------------------------------------------------
# DOE ORR Catalyst AST
# ---------------------------------------------------------------------------


class TestDOEORRCatalystAST:
    """Test DOE ORR Electrocatalyst AST protocol."""

    def test_creation(self):
        proto = DOEORRCatalystAST()
        assert isinstance(proto, StandardProtocol)

    def test_name(self):
        proto = DOEORRCatalystAST()
        assert proto.name == "DOE_ORR_Electrocatalyst_AST"

    def test_description_not_empty(self):
        proto = DOEORRCatalystAST()
        assert len(proto.description) > 0

    def test_to_procedure_returns_procedure(self):
        proto = DOEORRCatalystAST()
        proc = proto.to_procedure()
        assert isinstance(proc, Procedure)

    def test_to_procedure_has_phases(self):
        proto = DOEORRCatalystAST()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        assert len(ast.procedure) > 0

    def test_to_procedure_has_conditioning_phase(self):
        proto = DOEORRCatalystAST()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        phase_names = [p.name for p in ast.procedure]
        assert "Conditioning" in phase_names

    def test_to_procedure_has_ast_cycling_phase(self):
        proto = DOEORRCatalystAST()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        phase_names = [p.name for p in ast.procedure]
        assert "AST Cycling" in phase_names

    def test_to_procedure_has_initial_characterization(self):
        proto = DOEORRCatalystAST()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        phase_names = [p.name for p in ast.procedure]
        assert "Initial Characterization" in phase_names

    def test_to_procedure_has_final_characterization(self):
        proto = DOEORRCatalystAST()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        phase_names = [p.name for p in ast.procedure]
        assert "Final Characterization" in phase_names

    def test_to_procedure_system_has_3_electrodes(self):
        proto = DOEORRCatalystAST()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        assert ast.system.electrodes == 3

    def test_to_procedure_uses_rhe_reference(self):
        proto = DOEORRCatalystAST()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        assert ast.system.reference == "RHE"


# ---------------------------------------------------------------------------
# DOE OER Catalyst AST
# ---------------------------------------------------------------------------


class TestDOEOERCatalystAST:
    """Test DOE OER Electrocatalyst AST protocol."""

    def test_creation(self):
        proto = DOEOERCatalystAST()
        assert isinstance(proto, StandardProtocol)

    def test_name(self):
        proto = DOEOERCatalystAST()
        assert proto.name == "DOE_OER_Electrocatalyst_AST"

    def test_description_not_empty(self):
        proto = DOEOERCatalystAST()
        assert len(proto.description) > 0

    def test_to_procedure_returns_procedure(self):
        proto = DOEOERCatalystAST()
        proc = proto.to_procedure()
        assert isinstance(proc, Procedure)

    def test_to_procedure_has_phases(self):
        proto = DOEOERCatalystAST()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        assert len(ast.procedure) >= 2

    def test_has_conditioning_phase(self):
        proto = DOEOERCatalystAST()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        phase_names = [p.name for p in ast.procedure]
        assert "Conditioning" in phase_names

    def test_has_ast_cycling_phase(self):
        proto = DOEOERCatalystAST()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        phase_names = [p.name for p in ast.procedure]
        assert "AST Cycling" in phase_names


# ---------------------------------------------------------------------------
# DOE Catalyst Support AST
# ---------------------------------------------------------------------------


class TestDOECatalystSupportAST:
    """Test DOE Catalyst Support AST protocol."""

    def test_creation(self):
        proto = DOECatalystSupportAST()
        assert isinstance(proto, StandardProtocol)

    def test_name(self):
        proto = DOECatalystSupportAST()
        assert proto.name == "DOE_Catalyst_Support_AST"

    def test_description_not_empty(self):
        proto = DOECatalystSupportAST()
        assert len(proto.description) > 0

    def test_to_procedure_returns_procedure(self):
        proto = DOECatalystSupportAST()
        proc = proto.to_procedure()
        assert isinstance(proc, Procedure)

    def test_to_procedure_has_phases(self):
        proto = DOECatalystSupportAST()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        assert len(ast.procedure) >= 2


# ---------------------------------------------------------------------------
# JRC PEM Electrolysis
# ---------------------------------------------------------------------------


class TestJRCPEMElectrolysis:
    """Test JRC PEM Electrolysis protocol."""

    def test_creation(self):
        proto = JRCPEMElectrolysis()
        assert isinstance(proto, StandardProtocol)

    def test_name(self):
        proto = JRCPEMElectrolysis()
        assert proto.name == "JRC_PEM_Electrolysis"

    def test_description_not_empty(self):
        proto = JRCPEMElectrolysis()
        assert len(proto.description) > 0

    def test_to_procedure_returns_procedure(self):
        proto = JRCPEMElectrolysis()
        proc = proto.to_procedure()
        assert isinstance(proc, Procedure)

    def test_to_procedure_has_phases(self):
        proto = JRCPEMElectrolysis()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        assert len(ast.procedure) >= 2

    def test_has_break_in_phase(self):
        proto = JRCPEMElectrolysis()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        phase_names = [p.name for p in ast.procedure]
        assert "Break-in" in phase_names

    def test_has_characterization_phase(self):
        proto = JRCPEMElectrolysis()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        phase_names = [p.name for p in ast.procedure]
        assert "Characterization" in phase_names

    def test_uses_2_electrode_system(self):
        proto = JRCPEMElectrolysis()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        assert ast.system.electrodes == 2


# ---------------------------------------------------------------------------
# JRC Alkaline Electrolysis
# ---------------------------------------------------------------------------


class TestJRCAlkalineElectrolysis:
    """Test JRC Alkaline Electrolysis protocol."""

    def test_creation(self):
        proto = JRCAlkalineElectrolysis()
        assert isinstance(proto, StandardProtocol)

    def test_name(self):
        proto = JRCAlkalineElectrolysis()
        assert proto.name == "JRC_Alkaline_Electrolysis"

    def test_description_not_empty(self):
        proto = JRCAlkalineElectrolysis()
        assert len(proto.description) > 0

    def test_to_procedure_returns_procedure(self):
        proto = JRCAlkalineElectrolysis()
        proc = proto.to_procedure()
        assert isinstance(proc, Procedure)

    def test_to_procedure_has_phases(self):
        proto = JRCAlkalineElectrolysis()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        assert len(ast.procedure) >= 2

    def test_has_conditioning_phase(self):
        proto = JRCAlkalineElectrolysis()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        phase_names = [p.name for p in ast.procedure]
        assert "Conditioning" in phase_names

    def test_has_characterization_phase(self):
        proto = JRCAlkalineElectrolysis()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        phase_names = [p.name for p in ast.procedure]
        assert "Characterization" in phase_names

    def test_uses_2_electrode_system(self):
        proto = JRCAlkalineElectrolysis()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        assert ast.system.electrodes == 2

    def test_uses_koh_electrolyte(self):
        proto = JRCAlkalineElectrolysis()
        proc = proto.to_procedure()
        ast = proc.to_ast()
        # The electrolyte is set via the Procedure.system() call
        assert ast.system.electrolyte is not None
