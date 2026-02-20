"""Variable template resolution."""

from __future__ import annotations

import re
from typing import Any

_VAR_RE = re.compile(r"\{(\w+(?:\.\w+)*)\}")


def resolve_variables(template: str, context: dict[str, Any]) -> str:
    """Resolve {variable.path} placeholders in a template string.

    Args:
        template: String with {variable} or {variable.nested} placeholders.
        context: Dictionary of variable values (supports nested dicts).

    Returns:
        The template with all resolvable placeholders replaced.
    """
    def replacer(m: re.Match[str]) -> str:
        key = m.group(1)
        parts = key.split(".")
        val: Any = context
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part, m.group(0))
            else:
                return m.group(0)
        return str(val)
    return _VAR_RE.sub(replacer, template)


def has_variables(text: str) -> bool:
    """Check whether a string contains any {variable} placeholders."""
    return bool(_VAR_RE.search(text))
