"""DOE ORR Catalyst Activity/Stability Test built with the ecproc Python SDK.

Equivalent to doe_orr_catalyst_ast.ecproc: Full DOE ORR protocol with
5 phases - Conditioning, iR Compensation, Background, ORR Activity,
and Durability AST with checkpoint every 5000 cycles.
"""

from ecproc.sdk.procedure import Procedure

proc = Procedure(
    "DOE ORR Catalyst Activity/Stability Test",
    version="1.0",
    author="DOE Fuel Cell Consortium",
)

proc.system(
    electrodes=3,
    reference="RHE",
    working={
        "material": "Pt/C",
        "area_cm2": 0.196,
        "loading_ug_cm2": 20.0,
    },
    electrolyte=("HClO4", 0.1),
    counter="Pt mesh",
)

proc.safety(
    max_current="100 mA",
    voltage_window=["-0.05 V", "1.5 V"],
    temperature_limits=["15 C", "40 C"],
    stop_if=["current > 200 mA", "temperature > 45 C"],
)

# Phase 1: Conditioning
with proc.phase("Conditioning") as p:
    p.gas("N2")
    p.rotation(1600)
    p.cv(between="0.05 V and 1.2 V", rate="500 mV/s", cycles=50, tag="conditioning_cv")
    p.cv(between="0.05 V and 1.2 V", rate="50 mV/s", cycles=3, tag="conditioning_final")

# Phase 2: iR Compensation
with proc.phase("iR Compensation") as p:
    p.ocp(tag="ocp_stabilization", **{"for": "300 s"})
    p.eis(
        frequency="100 kHz to 0.1 Hz",
        amplitude="10 mV",
        dc_bias="0 V",
        tag="eis_ir",
        extract="Ru",
        vendor_flags={
            "biologic": {"bandwidth": 5, "drift_correction": True},
            "gamry": {"ac_settling": 3},
        },
    )

# Phase 3: Background
with proc.phase("Background") as p:
    p.gas("N2")
    p.rotation(1600)
    p.lsv(tag="background_n2", **{"from": "1.0 V", "to": "0.2 V", "rate": "20 mV/s"})
    p.lsv(tag="background_slow", **{"from": "1.0 V", "to": "0.2 V", "rate": "5 mV/s"})

# Phase 4: ORR Activity
with proc.phase("ORR Activity") as p:
    p.gas("O2")
    p.rotation(1600)
    p.stabilize("OCP stable within 5 mV for 60 s")
    p.lsv(tag="orr_20mVs", **{"from": "1.0 V", "to": "0.2 V", "rate": "20 mV/s"})
    p.lsv(tag="orr_5mVs", **{"from": "1.0 V", "to": "0.2 V", "rate": "5 mV/s"})

# Phase 5: Durability AST
with proc.phase("Durability AST") as p:
    p.gas("N2")
    p.rotation(0)
    loop = p.loop(30000)
    loop.cv(between="0.6 V and 1.0 V", rate="50 mV/s", cycles=1)

proc.state_recovery(
    after_pause=[{"ocp": {"for": "60 s"}}],
    after_checkpoint=[
        {"ocp": {"for": "30 s"}},
        {"eis": {
            "frequency": "100 kHz to 0.1 Hz",
            "amplitude": "10 mV",
            "dc_bias": "0 V",
        }},
    ],
    after_error=["log_error", {"ocp": {"for": "10 s"}}],
)

proc.output(ecdl={"include_raw": True, "compress": "gzip", "signing": "sha256"})

if __name__ == "__main__":
    result = proc.validate()
    print(f"Validation: {'PASS' if result.passed else 'FAIL'}")
    print(f"  Errors:   {len(result.errors)}")
    print(f"  Warnings: {len(result.warnings)}")
