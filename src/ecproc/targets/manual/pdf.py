"""PDF generation for manual target (requires reportlab)."""

from __future__ import annotations

from typing import Any


def render_pdf(sections: list[dict[str, Any]], output_path: str) -> None:
    """Render manual sections as PDF.

    Requires the 'pdf' extra: pip install ecproc[pdf]
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as e:
        raise ImportError(
            "PDF generation requires reportlab. Install with: pip install ecproc[pdf]"
        ) from e

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story: list[Any] = []

    story.append(Paragraph("Electrochemical Procedure", styles["Title"]))
    story.append(Spacer(1, 12))

    for section in sections:
        stype = section["type"]
        if stype == "phase":
            story.append(Paragraph(f"Phase: {section['name']}", styles["Heading2"]))
            for step in section.get("steps", []):
                tech = step.get("technique", "unknown")
                story.append(Paragraph(f"• {tech.upper()}", styles["Normal"]))
            story.append(Spacer(1, 6))

    doc.build(story)
