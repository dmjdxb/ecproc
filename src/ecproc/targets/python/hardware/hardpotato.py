"""Hard Potato potentiostat integration (stub)."""

from __future__ import annotations

from ecproc.targets.python.hardware.base import HardwareInterface


class HardPotatoHardware(HardwareInterface):
    """Hard Potato open-source potentiostat interface (stub)."""

    @property
    def name(self) -> str:
        return "hardpotato"

    def connect(self) -> None:
        raise NotImplementedError("HardPotato integration not yet implemented")

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
