"""CLI tests for the grouped evaluation command."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from reconstructor.cli import main
from reconstructor.evaluation import run_named, run_synthetic


def test_evaluate_synthetic_cli_passes_argv_without_mutating_sys_argv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: list[Sequence[str] | None] = []
    original_argv = list(sys.argv)

    def _fake_main(argv: Sequence[str] | None = None) -> int:
        captured.append(argv)
        return 7

    monkeypatch.setattr(run_synthetic, "main", _fake_main)

    result = main(
        [
            "evaluate",
            "synthetic",
            "--out",
            str(tmp_path),
            "--seeds-per-cell",
            "3",
        ]
    )

    assert result == 7
    assert captured == [["--out", str(tmp_path), "--seeds-per-cell", "3"]]
    assert sys.argv == original_argv


def test_evaluate_named_cli_passes_argv_without_mutating_sys_argv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: list[Sequence[str] | None] = []
    original_argv = list(sys.argv)

    def _fake_main(argv: Sequence[str] | None = None) -> int:
        captured.append(argv)
        return 11

    monkeypatch.setattr(run_named, "main", _fake_main)

    result = main(["evaluate", "named", "--out", str(tmp_path)])

    assert result == 11
    assert captured == [["--out", str(tmp_path)]]
    assert sys.argv == original_argv
