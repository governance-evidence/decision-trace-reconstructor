"""Tests for ``python -m reconstructor.cli``."""

from __future__ import annotations

import runpy

import pytest

import reconstructor.cli as cli


def test_python_module_entrypoint_delegates_to_cli_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "main", lambda: 13)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("reconstructor.cli.__main__", run_name="__main__")

    assert exc_info.value.code == 13
