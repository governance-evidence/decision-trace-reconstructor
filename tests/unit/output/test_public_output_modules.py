"""Public output package facade tests."""

from __future__ import annotations

import pytest

import reconstructor.adapters as adapters
import reconstructor.output as output


def test_output_facade_lazy_loads_public_modules() -> None:
    vars(output).pop("models", None)
    vars(output).pop("prov_jsonld", None)
    assert output.models.__name__ == "reconstructor.output.models"
    assert output.prov_jsonld.__name__ == "reconstructor.output.prov_jsonld"
    assert "models" in dir(output)
    assert "prov_jsonld" in dir(output)


def test_output_facade_rejects_private_modules() -> None:
    name = "missing"
    with pytest.raises(AttributeError, match="has no attribute 'missing'"):
        getattr(output, name)


def test_adapters_facade_rejects_unknown_adapter() -> None:
    name = "missing"
    with pytest.raises(AttributeError, match="has no attribute 'missing'"):
        getattr(adapters, name)
    assert "generic_jsonl" in dir(adapters)


def test_adapters_facade_lazy_loads_adapter_modules() -> None:
    vars(adapters).pop("generic_jsonl", None)
    assert adapters.generic_jsonl.__name__ == "reconstructor.adapters.generic_jsonl"
