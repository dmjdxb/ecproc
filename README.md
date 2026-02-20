# ecproc

A domain-specific language and toolchain for defining, validating, compiling, and executing electrochemical procedures.

## Overview

ecproc provides a complete pipeline for electrochemical experiment specification:

1. **Author** procedures in YAML (`.ecproc`) or programmatically via the Python SDK
2. **Parse** into a typed Abstract Syntax Tree (AST) with source-location tracking
3. **Generate** a validated Faraday Intermediate Representation (`.ir.json`) with SI unit normalization
4. **Validate** across 4 layers: syntax, electrochemistry, safety, and hardware compatibility
5. **Compile** to execution targets (Python runtime or human-readable manual)
6. **Execute** against real or mock potentiostat hardware
7. **Record** results as provenance-complete ECDL documents (`.ecdl.json`)

### Who it's for

- **Electrochemists** — write procedures in YAML with human-readable units (`50 mV/s`, `1 mA`, `60 s`)
- **ML/Data Engineers** — build procedures programmatically via the Python SDK for automated DOE campaigns
- **Lab Managers** — generate reproducible lab manuals in Markdown/PDF from the same procedure definition

## Architecture

```
.ecproc (YAML)  ──┐                                  ┌── Python Runtime
                   ├─→ AST ─→ Faraday IR ─→ Validate ─┤
SDK (Python)    ──┘                                  └── Manual (Markdown/PDF)
                                                           │
                                                           ▼
                                                      ECDL Record
```

| Module | Purpose | Files |
|--------|---------|-------|
| `parser` | YAML + Python SDK parsing → AST | 4 |
| `ir` | AST → Faraday IR with SI normalization | 4 |
| `validator` | 4-layer validation engine | 6 |
| `sdk` | Programmatic procedure builder | 16 |
| `targets` | Compilation + execution backends | 12 |
| `ecdl` | Output record generation + validation | 5 |
| `protocols` | Standard protocol templates (DOE, JRC) | 6 |
| `hardware_profiles` | Potentiostat capability profiles | 7 |
| `cli` | 8 CLI commands via Typer | 8 |
| `utils` | Units, time parsing, logging | 3 |

**86 source files, ~6,600 lines of production code.**

## Installation

```bash
pip install ecproc
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

### YAML (.ecproc)

```yaml
metadata:
  protocol: Simple CV
  version: "1.0"

system:
  electrodes: 3
  reference: RHE

procedure:
  - name: Conditioning
    steps:
      - cv:
          between: 0.05 V and 1.2 V
          rate: 50 mV/s
          cycles: 20
```

### Python SDK

```python
from ecproc import Procedure

proc = Procedure("Simple CV", version="1.0")
proc.system(electrodes=3, reference="RHE")

with proc.phase("Conditioning") as p:
    p.cv(between="0.05 V and 1.2 V", rate="50 mV/s", cycles=20)

result = proc.validate()
```

### CLI

```bash
ecproc parse my_procedure.ecproc          # Parse and display AST
ecproc validate my_procedure.ecproc       # Validate (L1-L4)
ecproc compile my_procedure.ecproc        # Compile to Python target
ecproc run my_procedure.ecproc            # Parse → validate → execute
ecproc execute my_procedure.ecproc        # Execute pre-compiled IR
ecproc manual my_procedure.ecproc         # Generate lab manual (Markdown)
ecproc convert my_procedure.ecproc        # Convert between formats
ecproc version                            # Show version
```

## Validation Levels

| Level | Name | Rules | Checks |
|-------|------|-------|--------|
| L1 | Syntax | SYN001–SYN005 | Required fields, valid techniques, type correctness |
| L2 | Electrochemistry | PV001–PV013, DR001–DR011 | Parameter bounds, domain rules, electrochemical constraints |
| L3 | Safety | SF001–SF007 | Voltage/current/temperature limits, thermal runaway detection, reference electrode monitoring |
| L4 | Hardware | HW001–HW003 | Potentiostat capability matching, technique support, range verification |

Validation stops early on L1 errors (structural problems) before running L2+ checks.

## Supported Techniques

| Technique | YAML Key | SDK Method | Description |
|-----------|----------|------------|-------------|
| Cyclic Voltammetry | `cv` | `p.cv()` | Potential sweep between vertices |
| Linear Sweep | `lsv` | `p.lsv()` | Single-direction potential sweep |
| Open Circuit Potential | `ocp` | `p.ocp()` | Monitor OCP over time |
| Chronoamperometry | `ca` / `hold` | `p.hold()` | Potentiostatic hold |
| Chronopotentiometry | `cp` / `galvanostatic` | `p.galvanostatic()` | Galvanostatic hold |
| EIS | `eis` | `p.eis()` | Electrochemical impedance spectroscopy |
| Differential Pulse | `dpv` | `p.dpv()` | Differential pulse voltammetry |
| Square Wave | `swv` | `p.swv()` | Square wave voltammetry |
| Galvanostatic Cycling | `gcd` | `p.gcd()` | Charge/discharge cycling |
| Constant Current | `cc` | `p.cc()` | Constant current hold |
| Stripping | `stripping` | `p.stripping()` | Stripping voltammetry |
| Purge | `purge` | `p.purge()` | Gas purge step |

## Unit Convention

| Layer | Units | Example |
|-------|-------|---------|
| YAML / Display | Human-friendly | `50 mV/s`, `1 mA`, `10 cm²`, `0.1 M`, `100 kHz` |
| Faraday IR | SI base | `0.05 V/s`, `0.001 A`, `0.001 m²`, `100 mol/m³`, `100000 Hz` |
| Temperature | °C in both | Electrochemistry convention |

The IR generator handles all unit conversions automatically.

## Hardware Profiles

Built-in profiles for common potentiostats:

- Gamry Interface 1010E / 1010B
- BioLogic SP-300
- PalmSens4
- Pine WaveDrive
- Mock (for testing/dry-run)

Profiles define supported techniques, voltage/current ranges, and frequency limits for L4 validation.

## Standard Protocols

Pre-built protocol templates following published standards:

- **DOE** — ORR catalyst, OER catalyst, catalyst support durability
- **JRC** — PEM electrolysis, alkaline electrolysis

## Quality

| Metric | Value |
|--------|-------|
| Tests | 1,196 |
| Coverage | 100% |
| Type checking | mypy --strict, 0 errors |
| Linting | ruff, 0 violations |

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run all quality gates
make all          # lint + typecheck + test

# Individual commands
make test         # pytest with coverage
make lint         # ruff check + format check
make typecheck    # mypy --strict
make fmt          # auto-fix lint + format
make clean        # remove caches
```

## Project Structure

```
ecproc/
├── src/ecproc/
│   ├── cli/              # 8 CLI commands (Typer)
│   ├── ecdl/             # ECDL record generation + validation
│   ├── hardware_profiles/ # Potentiostat JSON profiles
│   ├── ir/               # Faraday IR schema, generator, serializer
│   ├── parser/           # YAML + Python SDK parsers → AST
│   ├── protocols/        # DOE + JRC standard protocol templates
│   ├── sdk/              # Programmatic procedure builder + techniques
│   ├── targets/          # Python runtime + manual (Markdown/PDF)
│   ├── utils/            # Units, time, logging
│   └── validator/        # 4-layer validation engine
├── tests/                # 1,196 tests across 57 test files
├── schemas/              # JSON schemas (ECDL, Faraday IR, ecproc, hardware)
├── examples/             # Example .ecproc, .py, and .ecdl.json files
├── docs/                 # MkDocs documentation
└── .github/workflows/    # CI: test, lint, docs, release
```

## License

Apache 2.0
