# Contributing

## Development Setup

```bash
git clone https://github.com/electrocatalystai/ecproc.git
cd ecproc
pip install -e ".[dev,docs]"
```

## Running Tests

```bash
pytest tests/ -v
```

With coverage:

```bash
pytest tests/ --cov=ecproc --cov-fail-under=90
```

## Code Quality

### Type Checking

```bash
mypy --strict src/ecproc/
```

### Linting

```bash
ruff check src/ tests/
```

### Formatting

```bash
ruff format src/ tests/
```

## Project Structure

```
src/ecproc/
├── ast/            # AST node definitions (16 dataclasses)
├── cli/            # CLI commands (typer)
├── ecdl/           # ECDL schema, validator, generator, serializer
├── ir/             # Faraday IR Pydantic models, generator, serializer
├── parser/         # YAML and Python parsers
├── protocols/      # Standard protocol templates (DOE, JRC)
├── sdk/            # Python SDK (Procedure, Phase, techniques, triggers)
├── targets/        # Compilation targets (python, manual)
├── utils/          # Units, time, logging
└── validation/     # 4-layer validation engine (L1-L4)
```

## Quality Gates

All PRs must pass:

- `pytest` — 0 failures, 0 skipped
- `mypy --strict` — 0 errors
- `ruff check` — 0 violations
- Coverage — at least 90%
