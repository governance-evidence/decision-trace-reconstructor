# Development

## Local Checks

```bash
make install-dev
make check
pre-commit install
```

`make install-dev` installs the editable package with the same development and Parquet extras used by CI. `make check` runs Ruff, Ruff format check, mypy, pytest, and a package build.

## Evaluation Artifacts

```bash
decision-trace evaluate synthetic --out results/
decision-trace evaluate named --out results/
```

## Report Rendering

```bash
quarto render docs/report.qmd
```

The repository ships:

- 10 executable adapters with unit and integration coverage
- Pydantic v2 result models with published JSON Schema
- W3C PROV-O JSON-LD export
- Quarto-rendered evaluation report
- Generic JSONL mapping schema for custom-stack onboarding
- GitHub Actions CI matrix for Python 3.11 / 3.12 / 3.13 / 3.14

## Related

- [Installation](installation.md)
- [Roadmap](roadmap.md)
