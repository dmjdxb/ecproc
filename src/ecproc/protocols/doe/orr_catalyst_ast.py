"""DOE ORR Catalyst AST Protocol."""
from __future__ import annotations

from ecproc.protocols.base import StandardProtocol
from ecproc.sdk.procedure import Procedure


class DOEORRCatalystAST(StandardProtocol):
    name = "DOE_ORR_Electrocatalyst_AST"
    description = "DOE accelerated stress test for ORR electrocatalysts"

    def to_procedure(self) -> Procedure:
        proc = Procedure(self.name, version="1.0", author="DOE")
        proc.system(electrodes=3, reference="RHE", electrolyte=("HClO4", 0.1))
        with proc.phase("Conditioning") as p:
            p.setup(gas="N2")
            p.cv(vertex1=0.05, vertex2=1.2, rate=500, cycles=50)
        with proc.phase("Initial Characterization") as p:
            p.setup(gas="N2")
            p.cv(vertex1=0.05, vertex2=1.2, rate=20, cycles=3, tag="initial_cv")
            p.eis(f_start=100000, f_end=0.1, amplitude=10, tag="initial_eis")
        with proc.phase("AST Cycling") as p:
            p.setup(gas="N2")
            lp = p.loop(30000)
            lp.cv(vertex1=0.6, vertex2=1.0, rate=50, cycles=1)
        with proc.phase("Final Characterization") as p:
            p.setup(gas="N2")
            p.cv(vertex1=0.05, vertex2=1.2, rate=20, cycles=3, tag="final_cv")
            p.eis(f_start=100000, f_end=0.1, amplitude=10, tag="final_eis")
        return proc
