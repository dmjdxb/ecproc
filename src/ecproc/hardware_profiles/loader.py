"""Hardware profile loader."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PROFILES_DIR = Path(__file__).parent

def load_profile(name: str) -> dict[str, Any]:
    """Load a built-in hardware profile by name."""
    path = _PROFILES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Hardware profile not found: {name}")
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result

def load_profile_file(path: Path | str) -> dict[str, Any]:
    """Load a hardware profile from a file path."""
    p = Path(path)
    result: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    return result

def list_profiles() -> list[str]:
    """List available built-in profile names."""
    return [p.stem for p in _PROFILES_DIR.glob("*.json")]
