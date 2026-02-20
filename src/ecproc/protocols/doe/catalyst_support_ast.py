"""DOE Catalyst Support AST Protocol."""
from __future__ import annotations

from ecproc.protocols.base import StandardProtocol
from ecproc.sdk.procedure import Procedure


class DOECatalystSupportAST(StandardProtocol):
    name = "DOE_Catalyst_Support_AST"
    description = "DOE accelerated stress test for catalyst support durability"

    def to_procedure(self) -> Procedure:
        proc = Procedure(self.name, version="1.0", author="DOE")
        proc.system(electrodes=3, reference="RHE", electrolyte=("HClO4", 0.1))
        with proc.phase("Conditioning") as p:
            p.cv(vertex1=0.05, vertex2=1.2, rate=500, cycles=50)
        with proc.phase("AST Cycling") as p:
            lp = p.loop(5000)
            lp.cv(vertex1=1.0, vertex2=1.5, rate=500, cycles=1)
        return proc
