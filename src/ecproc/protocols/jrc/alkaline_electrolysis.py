"""JRC Alkaline Electrolysis Protocol."""
from __future__ import annotations

from ecproc.protocols.base import StandardProtocol
from ecproc.sdk.procedure import Procedure


class JRCAlkalineElectrolysis(StandardProtocol):
    name = "JRC_Alkaline_Electrolysis"
    description = "JRC harmonized test protocol for alkaline water electrolysis"

    def to_procedure(self) -> Procedure:
        proc = Procedure(self.name, version="1.0", author="JRC")
        proc.system(electrodes=2, reference="RHE", electrolyte=("KOH", 1.0))
        with proc.phase("Conditioning") as p:
            p.galvanostatic(current=0.5, duration=1800)
        with proc.phase("Characterization") as p:
            p.lsv(start=1.2, end=2.0, rate=1, tag="polarization")
        return proc
