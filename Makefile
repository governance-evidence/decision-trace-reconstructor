PYTHON ?= python

.PHONY: install-dev test lint format format-check typecheck build check

install-dev:
	$(PYTHON) -m pip install -e '.[dev,parquet]'

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check src tests scripts experiments

format:
	$(PYTHON) -m ruff format src tests scripts experiments

format-check:
	$(PYTHON) -m ruff format --check src tests scripts experiments

typecheck:
	$(PYTHON) -m mypy src

build:
	$(PYTHON) -m build

check: lint format-check typecheck test build

.PHONY: paper23-study
paper23-study:
	$(PYTHON) -m experiments.paper23 $(ARGS)
