"""Markdown output formatter for manual target."""

from __future__ import annotations

from typing import Any


def render_markdown(sections: list[dict[str, Any]], *, title: str = "Procedure") -> str:
    """Render manual sections as Markdown."""
    lines = [f"# {title}", ""]

    for section in sections:
        stype = section["type"]
        if stype == "equipment":
            lines.extend(_render_equipment(section))
        elif stype == "safety":
            lines.extend(_render_safety(section))
        elif stype == "phase":
            lines.extend(_render_phase(section))

    return "\n".join(lines)


def _render_equipment(section: dict[str, Any]) -> list[str]:
    lines = ["## Equipment", ""]
    sys = section.get("system", {})
    lines.append(f"- **Electrodes**: {sys.get('electrodes', 'N/A')}-electrode setup")
    lines.append(f"- **Reference**: {sys.get('reference', 'N/A')}")
    if sys.get("counter"):
        lines.append(f"- **Counter**: {sys['counter']}")
    lines.append("")
    return lines


def _render_safety(section: dict[str, Any]) -> list[str]:
    lines = [
        "## Safety Constraints",
        "",
        "**WARNING: Review all safety limits before proceeding.**",
        "",
    ]
    constraints = section.get("constraints", {})
    if constraints.get("max_current_A"):
        lines.append(f"- Max current: {constraints['max_current_A']} A")
    if constraints.get("voltage_window_V"):
        vw = constraints["voltage_window_V"]
        lines.append(f"- Voltage window: {vw[0]} V to {vw[1]} V")
    if constraints.get("temperature_limits_C"):
        tl = constraints["temperature_limits_C"]
        lines.append(f"- Temperature limits: {tl[0]}°C to {tl[1]}°C")
    lines.append("")
    return lines


def _render_phase(section: dict[str, Any]) -> list[str]:
    lines = [f"## Phase: {section['name']}", ""]
    if section.get("setup"):
        lines.append(f"**Setup**: {section['setup']}")
        lines.append("")
    if section.get("stabilize"):
        lines.append(f"**Stabilize**: {', '.join(section['stabilize'])}")
        lines.append("")

    for i, step in enumerate(section.get("steps", []), 1):
        if step.get("type") == "loop":
            lines.append(f"{i}. **Loop** ({step['count']} iterations):")
            for j, s in enumerate(step.get("steps", []), 1):
                lines.append(f"   {i}.{j}. {_format_step(s)}")
        else:
            lines.append(f"{i}. {_format_step(step)}")

    if section.get("teardown"):
        lines.append("")
        lines.append(f"**Teardown**: {section['teardown']}")
    lines.append("")
    return lines


def _format_step(step: dict[str, Any]) -> str:
    tech = step.get("technique", "unknown")
    params = step.get("parameters", {})
    param_str = ", ".join(f"{k}={v}" for k, v in params.items())
    tag = f" [tag: {step['tag']}]" if step.get("tag") else ""
    return f"**{tech.upper()}**({param_str}){tag}"
