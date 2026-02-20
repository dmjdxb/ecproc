"""Raw data collection and file management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DataHandler:
    """Manages raw data files from procedure execution."""

    def __init__(self, output_dir: Path | str = ".") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._files: list[str] = []

    def save_step_data(self, tag: str, technique: str, data: dict[str, Any]) -> str:
        """Save raw data from a step execution."""
        filename = f"{tag}_{technique}.json"
        filepath = self.output_dir / filename
        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        self._files.append(str(filepath))
        return str(filepath)

    @property
    def files(self) -> list[str]:
        return list(self._files)
