# ecproc

**Domain-specific language and toolchain for electrochemical procedures.**

ecproc provides a complete workflow for defining, validating, compiling, and executing electrochemical experiments — from human-readable YAML protocols to instrument-ready instructions.

## Features

- **ECDL (Electrochemical Description Language)** — YAML-based DSL for defining experimental procedures
- **Python SDK** — Programmatic procedure construction with full type safety
- **4-Layer Validation** — Syntax, electrochemistry rules, safety checks, and hardware compatibility
- **Faraday IR** — Intermediate representation with SI unit normalization
- **Multiple Targets** — Compile to executable Python or human-readable manuals
- **Standard Protocols** — Built-in DOE and JRC protocol templates
- **Hardware Profiles** — Pre-configured support for Gamry, BioLogic, PalmSens, and Pine instruments

## Quick Example

```yaml
# simple_cv.ecproc
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

```bash
ecproc validate simple_cv.ecproc
ecproc compile simple_cv.ecproc -o output.json
ecproc run simple_cv.ecproc --target python
```

## Architecture

```
.ecproc YAML ──► Parser ──► AST ──► IR Generator ──► Faraday IR ──► Target Compiler
                                         │                              │
                                    Validation              Python / Manual / ...
                                   (L1─L4)
```
