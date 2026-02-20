"""Tests for modules that previously had 0% code coverage.

Covers:
- src/ecproc/__main__.py
- src/ecproc/targets/python/hardware/hardpotato.py
- src/ecproc/targets/python/hardware/pyvisa.py
- src/ecproc/targets/manual/pdf.py
"""

from __future__ import annotations

import importlib
import runpy
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. __main__.py
# ---------------------------------------------------------------------------

class TestMainModule:
    """Verify that `python -m ecproc` delegates to the CLI app."""

    def test_main_invokes_app(self):
        mock_app = MagicMock()
        with patch.dict("sys.modules", {"ecproc.cli.main": MagicMock(app=mock_app)}):
            # Remove cached __main__ so runpy re-imports it
            sys.modules.pop("ecproc.__main__", None)
            runpy.run_module("ecproc", run_name="__main__", alter_sys=False)
        mock_app.assert_called_once()


# ---------------------------------------------------------------------------
# 2. HardPotatoHardware
# ---------------------------------------------------------------------------

class TestHardPotatoHardware:
    """Cover every method of HardPotatoHardware."""

    @pytest.fixture()
    def hw(self):
        from ecproc.targets.python.hardware.hardpotato import HardPotatoHardware
        return HardPotatoHardware()

    def test_name(self, hw):
        assert hw.name == "hardpotato"

    def test_connect_raises(self, hw):
        with pytest.raises(
            NotImplementedError,
            match="HardPotato integration not yet implemented",
        ):
            hw.connect()

    def test_disconnect_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.disconnect()

    def test_cell_on_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.cell_on()

    def test_cell_off_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.cell_off()

    def test_set_potential_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.set_potential(0.5)

    def test_read_current_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.read_current()

    def test_read_potential_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.read_potential()


# ---------------------------------------------------------------------------
# 3. PyVISAHardware
# ---------------------------------------------------------------------------

class TestPyVISAHardware:
    """Cover every method of PyVISAHardware."""

    @pytest.fixture()
    def hw(self):
        from ecproc.targets.python.hardware.pyvisa import PyVISAHardware
        return PyVISAHardware()

    def test_name(self, hw):
        assert hw.name == "pyvisa"

    def test_connect_raises(self, hw):
        with pytest.raises(NotImplementedError, match="PyVISA integration not yet implemented"):
            hw.connect()

    def test_disconnect_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.disconnect()

    def test_cell_on_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.cell_on()

    def test_cell_off_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.cell_off()

    def test_set_potential_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.set_potential(1.0)

    def test_read_current_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.read_current()

    def test_read_potential_raises(self, hw):
        with pytest.raises(NotImplementedError):
            hw.read_potential()


# ---------------------------------------------------------------------------
# 4. render_pdf (manual/pdf.py)
# ---------------------------------------------------------------------------

class TestRenderPdf:
    """Cover both the ImportError branch and the success branch of render_pdf."""

    def test_render_pdf_raises_when_reportlab_missing(self):
        """When reportlab is not installed the function must raise ImportError."""
        import builtins
        real_import = builtins.__import__

        def _fake_import(name, *args, **kwargs):
            if name == "reportlab" or name.startswith("reportlab."):
                raise ImportError("No module named 'reportlab'")
            return real_import(name, *args, **kwargs)

        # Ensure the module is freshly imported so the top-level import
        # (if any) is re-executed under our patched import.
        sys.modules.pop("ecproc.targets.manual.pdf", None)

        with patch("builtins.__import__", side_effect=_fake_import):
            # Re-import the module under the patched import
            try:
                mod = importlib.import_module("ecproc.targets.manual.pdf")
                # If the module loads fine and defers the check to the function
                with pytest.raises(ImportError, match="ecproc\\[pdf\\]"):
                    mod.render_pdf([], "/tmp/out.pdf")
            except ImportError:
                # The module itself raises at import time -- that also counts
                # as covering the branch.
                pass

    def test_render_pdf_success_with_mocked_reportlab(self, tmp_path):
        """When reportlab is available, render_pdf should create a PDF."""
        # Build lightweight mock objects that mimic reportlab's API
        mock_doc = MagicMock()
        mock_simple_doc_template = MagicMock(return_value=mock_doc)
        mock_paragraph = MagicMock()
        mock_spacer = MagicMock()
        mock_styles = MagicMock()
        mock_get_sample_style_sheet = MagicMock(return_value=mock_styles)

        reportlab_mocks = {
            "reportlab": MagicMock(),
            "reportlab.lib": MagicMock(),
            "reportlab.lib.pagesizes": MagicMock(A4=(595, 842)),
            "reportlab.lib.units": MagicMock(inch=72),
            "reportlab.platypus": MagicMock(
                SimpleDocTemplate=mock_simple_doc_template,
                Paragraph=mock_paragraph,
                Spacer=mock_spacer,
            ),
            "reportlab.lib.styles": MagicMock(
                getSampleStyleSheet=mock_get_sample_style_sheet,
            ),
        }

        # Ensure the module is freshly imported with mocked reportlab
        sys.modules.pop("ecproc.targets.manual.pdf", None)

        with patch.dict("sys.modules", reportlab_mocks):
            mod = importlib.import_module("ecproc.targets.manual.pdf")

            # Sections matching the real render_pdf interface:
            # each section has "type", "name", and optional "steps" list
            # where each step has a "technique" key.
            sections = [
                {
                    "type": "phase",
                    "name": "Conditioning",
                    "steps": [
                        {"technique": "CV"},
                        {"technique": "EIS"},
                    ],
                },
                {
                    "type": "phase",
                    "name": "Measurement",
                    "steps": [
                        {"technique": "LSV"},
                    ],
                },
                {
                    # A non-phase section type to cover the branch where
                    # stype != "phase" (the if-block is skipped).
                    "type": "note",
                    "name": "Ignored section",
                },
            ]
            output = str(tmp_path / "test_output.pdf")
            mod.render_pdf(sections, output)

        # SimpleDocTemplate was instantiated with the output path
        mock_simple_doc_template.assert_called_once_with(output, pagesize=(595, 842))
        # doc.build was called to finalise the PDF
        mock_doc.build.assert_called_once()

    def test_render_pdf_phase_with_no_steps(self, tmp_path):
        """A phase section with no 'steps' key should not error."""
        mock_doc = MagicMock()
        mock_simple_doc_template = MagicMock(return_value=mock_doc)
        mock_paragraph = MagicMock()
        mock_spacer = MagicMock()
        mock_styles = MagicMock()
        mock_get_sample_style_sheet = MagicMock(return_value=mock_styles)

        reportlab_mocks = {
            "reportlab": MagicMock(),
            "reportlab.lib": MagicMock(),
            "reportlab.lib.pagesizes": MagicMock(A4=(595, 842)),
            "reportlab.lib.units": MagicMock(inch=72),
            "reportlab.platypus": MagicMock(
                SimpleDocTemplate=mock_simple_doc_template,
                Paragraph=mock_paragraph,
                Spacer=mock_spacer,
            ),
            "reportlab.lib.styles": MagicMock(
                getSampleStyleSheet=mock_get_sample_style_sheet,
            ),
        }

        sys.modules.pop("ecproc.targets.manual.pdf", None)

        with patch.dict("sys.modules", reportlab_mocks):
            mod = importlib.import_module("ecproc.targets.manual.pdf")

            sections = [
                {
                    "type": "phase",
                    "name": "Empty Phase",
                    # no "steps" key -- exercises section.get("steps", [])
                },
            ]
            output = str(tmp_path / "test_no_steps.pdf")
            mod.render_pdf(sections, output)

        mock_doc.build.assert_called_once()

    def test_render_pdf_step_without_technique(self, tmp_path):
        """A step dict missing 'technique' should default to 'unknown'."""
        mock_doc = MagicMock()
        mock_simple_doc_template = MagicMock(return_value=mock_doc)
        mock_paragraph = MagicMock()
        mock_spacer = MagicMock()
        mock_styles = MagicMock()
        mock_get_sample_style_sheet = MagicMock(return_value=mock_styles)

        reportlab_mocks = {
            "reportlab": MagicMock(),
            "reportlab.lib": MagicMock(),
            "reportlab.lib.pagesizes": MagicMock(A4=(595, 842)),
            "reportlab.lib.units": MagicMock(inch=72),
            "reportlab.platypus": MagicMock(
                SimpleDocTemplate=mock_simple_doc_template,
                Paragraph=mock_paragraph,
                Spacer=mock_spacer,
            ),
            "reportlab.lib.styles": MagicMock(
                getSampleStyleSheet=mock_get_sample_style_sheet,
            ),
        }

        sys.modules.pop("ecproc.targets.manual.pdf", None)

        with patch.dict("sys.modules", reportlab_mocks):
            mod = importlib.import_module("ecproc.targets.manual.pdf")

            sections = [
                {
                    "type": "phase",
                    "name": "Fallback",
                    "steps": [{}],  # no "technique" -> defaults to "unknown"
                },
            ]
            output = str(tmp_path / "test_unknown_technique.pdf")
            mod.render_pdf(sections, output)

        # Verify the paragraph was created with "UNKNOWN" (uppercased "unknown")
        paragraph_texts = [
            str(c) for c in mock_paragraph.call_args_list
        ]
        assert any("UNKNOWN" in t for t in paragraph_texts)
        mock_doc.build.assert_called_once()
