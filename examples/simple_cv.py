"""Simple CV procedure built with the ecproc Python SDK.

Equivalent to simple_cv.ecproc: 3-electrode system with RHE reference,
one phase with CV between 0.05 V and 1.2 V at 50 mV/s for 20 cycles.
"""

from ecproc.sdk.procedure import Procedure

proc = Procedure("Simple CV", version="1.0")
proc.system(electrodes=3, reference="RHE")

with proc.phase("Conditioning") as p:
    p.cv(between="0.05 V and 1.2 V", rate="50 mV/s", cycles=20)

if __name__ == "__main__":
    result = proc.validate()
    print(f"Validation: {'PASS' if result.passed else 'FAIL'}")
