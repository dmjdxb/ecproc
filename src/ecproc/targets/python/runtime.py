"""Python target runtime - execution engine."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from ecproc.targets.base import ExecutionResult


class PythonRuntime:
    """Execute compiled Python instructions on hardware."""

    def __init__(self, hardware: Any) -> None:
        self.hardware = hardware
        self.observations: list[dict[str, Any]] = []
        self.data_files: list[str] = []

    def execute(
        self, instructions: list[dict[str, Any]], *, dry_run: bool = False
    ) -> ExecutionResult:
        """Execute compiled instructions."""
        started = datetime.now(timezone.utc).isoformat()
        errors: list[str] = []

        try:
            if not dry_run:
                self.hardware.connect()

            for inst in instructions:
                if dry_run:
                    continue
                self._execute_instruction(inst)

            if not dry_run:
                self.hardware.disconnect()

        except Exception as e:
            errors.append(str(e))

        completed = datetime.now(timezone.utc).isoformat()

        return ExecutionResult(
            success=len(errors) == 0,
            target="python",
            observations=self.observations,
            data_files=self.data_files,
            errors=errors,
            started=started,
            completed=completed,
            hardware=getattr(self.hardware, "name", "unknown"),
        )

    def _execute_instruction(self, inst: dict[str, Any]) -> None:
        itype = inst["type"]
        if itype == "step":
            self._execute_step(inst)
        elif itype == "loop":
            self._execute_loop(inst)
        elif itype == "phase_start":
            pass  # Setup handled by hardware
        elif itype == "phase_end":
            pass
        elif itype == "stabilize":
            time.sleep(0.01)  # Simulated wait

    def _execute_step(self, inst: dict[str, Any]) -> None:
        technique = inst["technique"]
        params = inst.get("parameters", {})
        method = getattr(self.hardware, f"run_{technique}", None)
        if method:
            result = method(**params)
            if inst.get("tag") and result is not None:
                self.observations.append({
                    "tag": inst["tag"],
                    "technique": technique,
                    "data": result,
                })

    def _execute_loop(self, inst: dict[str, Any]) -> None:
        count = inst["count"]
        if isinstance(count, int):
            for _ in range(count):
                for step in inst["steps"]:
                    self._execute_instruction(step)
