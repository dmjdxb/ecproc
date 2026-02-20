"""DOE OER Catalyst AST Protocol."""
from __future__ import annotations

from ecproc.protocols.base import StandardProtocol
from ecproc.sdk.procedure import Procedure


class DOEOERCatalystAST(StandardProtocol):
    name = "DOE_OER_Electrocatalyst_AST"
    description = "DOE accelerated stress test for OER electrocatalysts"

    def to_procedure(self) -> Procedure:
        proc = Procedure(self.name, version="1.0", author="DOE")
        proc.system(electrodes=3, reference="RHE", electrolyte=("H2SO4", 0.5))
        with proc.phase("Conditioning") as p:
            p.cv(vertex1=1.2, vertex2=1.6, rate=100, cycles=20)
        with proc.phase("AST Cycling") as p:
            lp = p.loop(10000)
            lp.hold(potential=1.6, duration=10)
            lp.hold(potential=1.0, duration=10)
        return proc
