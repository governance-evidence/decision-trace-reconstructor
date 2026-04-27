"""Output writers for the result artifacts.

Each evaluation runner produces four canonical artifacts; this package
defines the typed schema (``models``) and the alternative serializations:

- raw JSON (default; produced by the runners directly)
- JSON Schema (``models`` -> ``docs/schemas/`` via ``scripts/export_schemas.py``)
- W3C PROV-O JSON-LD (``prov_jsonld``; semantic governance-grade trace)
- Apache Parquet sibling files, emitted by the evaluation runner when the
  optional ``[parquet]`` extra is installed
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

__all__ = ["models", "prov_jsonld"]


def __getattr__(name: str) -> ModuleType:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    return sorted([*globals(), *__all__])
