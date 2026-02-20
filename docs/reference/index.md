# API Reference

## Core Modules

### Parser

::: ecproc.parser.yaml_parser.YAMLParser
    options:
      show_root_heading: true
      members: [parse_file, parse_string]

### IR Schema

::: ecproc.ir.schema.FaradayIR
    options:
      show_root_heading: true

### Validation

::: ecproc.validator.engine
    options:
      show_root_heading: true

### SDK

::: ecproc.sdk.procedure.Procedure
    options:
      show_root_heading: true
      members: [system, phase, safety, compile, validate]

### ECDL

::: ecproc.ecdl.validator
    options:
      show_root_heading: true
      members: [validate_ecdl, validate_physics_invariants, validate_semantics]

## Targets

### Python Target

::: ecproc.targets.python.PythonTarget
    options:
      show_root_heading: true

### Manual Target

::: ecproc.targets.manual.ManualTarget
    options:
      show_root_heading: true
