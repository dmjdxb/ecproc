"""Mock hardware for testing - simulated potentiostat."""

from __future__ import annotations

import math
import random
from typing import Any

from ecproc.targets.python.hardware.base import HardwareInterface


class MockHardware(HardwareInterface):
    """Simulated potentiostat for testing."""

    @property
    def name(self) -> str:
        return "mock"

    def __init__(self) -> None:
        self._connected = False
        self._cell_on = False
        self._potential = 0.0
        self._current = 0.0

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def cell_on(self) -> None:
        self._cell_on = True

    def cell_off(self) -> None:
        self._cell_on = False

    def set_potential(self, potential_v: float) -> None:
        self._potential = potential_v

    def read_current(self) -> float:
        return self._current + random.gauss(0, 1e-6)

    def read_potential(self) -> float:
        return self._potential + random.gauss(0, 1e-4)

    def run_cv(self, **kwargs: Any) -> dict[str, Any]:
        n_points = 100
        vertex1 = kwargs.get("vertex1", 0.0)
        vertex2 = kwargs.get("vertex2", 1.0)
        potentials = []
        currents = []
        for i in range(n_points):
            frac = i / n_points
            e = vertex1 + (vertex2 - vertex1) * (0.5 - 0.5 * math.cos(2 * math.pi * frac))
            j = 0.001 * math.sin(2 * math.pi * frac) + random.gauss(0, 1e-5)
            potentials.append(e)
            currents.append(j)
        return {"potentials_V": potentials, "currents_A": currents}

    def run_ocp(self, **kwargs: Any) -> dict[str, Any]:
        return {"ocp_V": 0.05 + random.gauss(0, 0.01)}

    def run_eis(self, **kwargs: Any) -> dict[str, Any]:
        return {"Z_real": [100, 50, 25], "Z_imag": [-10, -30, -5], "freq_Hz": [1e5, 1e3, 1]}

    def run_lsv(self, **kwargs: Any) -> dict[str, Any]:
        return {"potentials_V": [0.0, 0.5, 1.0], "currents_A": [0.0, 0.001, 0.01]}

    def run_hold(self, **kwargs: Any) -> dict[str, Any]:
        return {"current_A": 0.001, "potential_V": kwargs.get("potential", 0.5)}

    def run_galvanostatic(self, **kwargs: Any) -> dict[str, Any]:
        return {"potential_V": 1.5, "current_A": kwargs.get("current", 0.01)}

    def run_dpv(self, **kwargs: Any) -> dict[str, Any]:
        return {"potentials_V": [0.0, 0.3, 0.6], "currents_A": [0.0, 0.005, 0.001]}

    def run_swv(self, **kwargs: Any) -> dict[str, Any]:
        return {"potentials_V": [0.0, 0.3, 0.6], "currents_A": [0.0, 0.004, 0.001]}

    def run_gcd(self, **kwargs: Any) -> dict[str, Any]:
        return {"time_s": [0, 100, 200], "potential_V": [0.0, 0.8, 0.0]}

    def run_cc(self, **kwargs: Any) -> dict[str, Any]:
        return {"charge_C": 0.01, "time_s": 10.0}

    def run_stripping(self, **kwargs: Any) -> dict[str, Any]:
        return {"potentials_V": [0.0, 0.5, 1.0], "currents_A": [0.0, 0.01, 0.001]}

    def run_purge(self, **kwargs: Any) -> dict[str, Any]:
        return {"gas": kwargs.get("gas", "N2"), "duration_s": kwargs.get("duration", 300)}
