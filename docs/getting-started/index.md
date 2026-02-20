# Getting Started

## Installation

Install ecproc from source:

```bash
pip install -e "."
```

For development (includes test and lint tools):

```bash
pip install -e ".[dev]"
```

For PDF manual generation:

```bash
pip install -e ".[pdf]"
```

## Verify Installation

```bash
ecproc version
```

## Your First Procedure

Create a file called `my_experiment.ecproc`:

```yaml
metadata:
  protocol: My First Experiment
  version: "1.0"
  author: Your Name

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

  - name: Measurement
    steps:
      - lsv:
          from: 1.0 V
          to: 0.2 V
          rate: 5 mV/s
```

## Validate

```bash
ecproc validate my_experiment.ecproc
```

## Compile

```bash
ecproc compile my_experiment.ecproc -o compiled.json
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `ecproc parse` | Parse .ecproc file to AST |
| `ecproc validate` | Validate procedure (L1-L4) |
| `ecproc compile` | Compile to Faraday IR |
| `ecproc run` | Execute procedure on target |
| `ecproc execute` | Full parse-validate-compile-run pipeline |
| `ecproc convert` | Convert between formats |
| `ecproc manual` | Generate human-readable manual |
| `ecproc version` | Show version info |
