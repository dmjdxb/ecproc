.PHONY: test lint typecheck fmt all install clean

test:
	pytest tests/ -v --cov=ecproc --cov-report=term-missing

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

typecheck:
	mypy --strict src/ecproc/

fmt:
	ruff check --fix src/ tests/
	ruff format src/ tests/

all: lint typecheck test

install:
	pip install -e ".[dev]"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info src/*.egg-info
