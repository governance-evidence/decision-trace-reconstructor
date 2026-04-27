"""Dynamic discovery of adapter-owned CLI integrations."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from importlib import import_module
from pkgutil import iter_modules
from typing import Any, Protocol, cast

from .. import adapters


class _RegisterIngestParser(Protocol):
    def __call__(
        self,
        p_ingest_sub: argparse._SubParsersAction[argparse.ArgumentParser],
    ) -> None: ...


def iter_adapter_ingest_registrars() -> Iterator[tuple[str, _RegisterIngestParser]]:
    """Yield ingest parser registrars exposed by adapter packages."""
    adapter_paths = cast(Any, adapters.__path__)
    adapter_names = sorted(
        info.name
        for info in iter_modules(adapter_paths)
        if info.ispkg and not info.name.startswith("_")
    )

    for adapter_name in adapter_names:
        module_name = f"{adapters.__name__}.{adapter_name}.cli"
        try:
            module = import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                continue
            raise

        registrar = getattr(module, "register_ingest_parser", None)
        if callable(registrar):
            yield adapter_name, cast(_RegisterIngestParser, registrar)
