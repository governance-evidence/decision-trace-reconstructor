"""Tests for adapter-owned CLI discovery."""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from reconstructor import adapters
from reconstructor.cli import adapter_registry
from reconstructor.cli.adapter_registry import iter_adapter_ingest_registrars


def test_adapter_registry_discovers_adapter_cli_modules() -> None:
    package_path = Path(next(iter(adapters.__path__)))
    expected = sorted(path.parent.name for path in package_path.glob("*/cli.py"))

    discovered = {
        adapter_name: register_ingest_parser
        for adapter_name, register_ingest_parser in iter_adapter_ingest_registrars()
    }

    assert sorted(discovered) == expected
    assert all(callable(register) for register in discovered.values())


def test_adapter_registry_skips_adapters_without_cli_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _register(
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    ) -> None:
        assert subparsers is not None

    monkeypatch.setattr(
        adapter_registry,
        "iter_modules",
        lambda _paths: [
            SimpleNamespace(name="no_cli", ispkg=True),
            SimpleNamespace(name="with_cli", ispkg=True),
        ],
    )

    def _import_module(module_name: str) -> object:
        if module_name.endswith(".no_cli.cli"):
            raise ModuleNotFoundError(name=module_name)
        return SimpleNamespace(register_ingest_parser=_register)

    monkeypatch.setattr(adapter_registry, "import_module", _import_module)

    assert list(iter_adapter_ingest_registrars()) == [("with_cli", _register)]


def test_adapter_registry_reraises_missing_adapter_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        adapter_registry,
        "iter_modules",
        lambda _paths: [SimpleNamespace(name="broken", ispkg=True)],
    )

    def _import_module(_module_name: str) -> object:
        raise ModuleNotFoundError(name="missing_dependency")

    monkeypatch.setattr(adapter_registry, "import_module", _import_module)

    with pytest.raises(ModuleNotFoundError):
        list(iter_adapter_ingest_registrars())
