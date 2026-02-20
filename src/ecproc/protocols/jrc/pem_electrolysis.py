"""JRC PEM Electrolysis Protocol."""
from __future__ import annotations

from ecproc.protocols.base import StandardProtocol
from ecproc.sdk.procedure import Procedure


class JRCPEMElectrolysis(StandardProtocol):
    name = "JRC_PEM_Electrolysis"
    description = "JRC harmonized test protocol for PEM water electrolysis"

    def to_procedure(self) -> Procedure:
        proc = Procedure(self.name, version="1.0", author="JRC")
        proc.system(electrodes=2, reference="RHE")
        with proc.phase("Break-in") as p:
            p.galvanostatic(current=1.0, duration=3600)
        with proc.phase("Characterization") as p:
            p.lsv(start=1.2, end=2.0, rate=1, tag="polarization")
            p.eis(f_start=100000, f_end=0.1, amplitude=10, tag="impedance")
        return proc
