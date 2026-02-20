"""Abstract hardware interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class HardwareInterface(ABC):
    """Abstract interface for potentiostat hardware."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def cell_on(self) -> None:
        ...

    @abstractmethod
    def cell_off(self) -> None:
        ...

    @abstractmethod
    def set_potential(self, potential_v: float) -> None:
        ...

    @abstractmethod
    def read_current(self) -> float:
        ...

    @abstractmethod
    def read_potential(self) -> float:
        ...
