"""Parquet sibling writer tests with explicit optional-dependency coverage."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from reconstructor.evaluation.synthetic_outputs import _maybe_write_parquet

RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"


class _FakeArrowTable:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    @classmethod
    def from_pylist(cls, rows: list[dict[str, Any]]) -> _FakeArrowTable:
        return cls(rows)


def test_parquet_writer_uses_pyarrow_when_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    rows = json.loads((RESULTS_DIR / "per_scenario.json").read_text())
    out = tmp_path / "per_scenario.parquet"

    fake_pyarrow = ModuleType("pyarrow")
    fake_parquet = ModuleType("pyarrow.parquet")
    calls: dict[str, Any] = {}

    def _write_table(table: _FakeArrowTable, path: Path, compression: str) -> None:
        calls["rows"] = table.rows
        calls["path"] = path
        calls["compression"] = compression
        path.write_text("fake parquet\n")

    fake_pyarrow.__path__ = []
    fake_pyarrow.Table = _FakeArrowTable
    fake_pyarrow.parquet = fake_parquet
    fake_parquet.write_table = _write_table
    monkeypatch.setitem(sys.modules, "pyarrow", fake_pyarrow)
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", fake_parquet)

    _maybe_write_parquet(out, rows)

    assert out.exists()
    assert calls == {"rows": rows, "path": out, "compression": "snappy"}


def test_parquet_writer_noops_when_pyarrow_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    monkeypatch.delitem(sys.modules, "pyarrow.parquet", raising=False)

    out = tmp_path / "missing_dependency.parquet"
    _maybe_write_parquet(out, [{"scenario_id": "s1"}])

    assert not out.exists()


def test_parquet_writer_noops_on_empty_rows(tmp_path: Path) -> None:
    out = tmp_path / "empty.parquet"
    _maybe_write_parquet(out, [])
    assert not out.exists()
