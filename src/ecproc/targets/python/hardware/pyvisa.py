"""PyVISA instrument communication (stub)."""

from __future__ import annotations

from ecproc.targets.python.hardware.base import HardwareInterface


class PyVISAHardware(HardwareInterface):
    """PyVISA-based instrument interface (stub)."""

    @property
    def name(self) -> str:
        return "pyvisa"

    def connect(self) -> None:
        raise NotImplementedError("PyVISA integration not yet implemented")

    def disconnect(self) -> None:
        raise NotImplementedError

    def cell_on(self) -> None:
        raise NotImplementedError

    def cell_off(self) -> None:
        raise NotImplementedError

    def set_potential(self, potential_v: float) -> None:
        raise NotImplementedError

    def read_current(self) -> float:
        raise NotImplementedError

    def read_potential(self) -> float:
        raise NotImplementedError
