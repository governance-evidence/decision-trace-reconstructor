"""Tests for LangSmith SDK boundary helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from reconstructor.adapters.langsmith.network import fetch_run_subtree, fetch_trace


@dataclass
class _FakeRun:
    id: str
    name: str = "write_report"
    run_type: str = "tool"
    start_time: str = "2025-01-01T00:00:00Z"
    end_time: str = "2025-01-01T00:00:01Z"
    parent_run_id: str | None = None
    trace_id: str = "trace-001"
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    session_id: str | None = None
    status: str = "success"
    child_runs: list[_FakeRun] | None = None


class _TraceClient:
    def __init__(self, runs: list[_FakeRun]) -> None:
        self.runs = runs
        self.calls: list[dict[str, str | None]] = []

    def list_runs(
        self,
        *,
        project_name: str | None = None,
        trace: str | None = None,
    ) -> list[_FakeRun]:
        self.calls.append({"project_name": project_name, "trace": trace})
        return self.runs


class _SubtreeClient:
    def __init__(self, root: _FakeRun) -> None:
        self.root = root
        self.read_run_id: str | None = None
        self.load_child_runs: bool | None = None

    def read_run(self, run_id: str, *, load_child_runs: bool = False) -> _FakeRun:
        self.read_run_id = run_id
        self.load_child_runs = load_child_runs
        return self.root


def test_fetch_trace_uses_project_filter_and_serialises_runs() -> None:
    client = _TraceClient(
        [
            _FakeRun(
                id="run-1",
                inputs={"path": "report.md"},
                tags=["reviewed"],
            )
        ]
    )

    runs = fetch_trace(client, "trace-001", project_name="production")

    assert client.calls == [{"project_name": "production", "trace": "trace-001"}]
    assert runs == [
        {
            "id": "run-1",
            "name": "write_report",
            "run_type": "tool",
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2025-01-01T00:00:01Z",
            "parent_run_id": None,
            "trace_id": "trace-001",
            "inputs": {"path": "report.md"},
            "outputs": {},
            "error": None,
            "tags": ["reviewed"],
            "extra": {},
            "events": [],
            "session_id": None,
            "status": "success",
        }
    ]


def test_fetch_run_subtree_reads_children_recursively() -> None:
    grandchild = _FakeRun(id="grandchild", parent_run_id="child")
    child = _FakeRun(id="child", parent_run_id="root", child_runs=[grandchild])
    root = _FakeRun(id="root", child_runs=[child])
    client = _SubtreeClient(root)

    runs = fetch_run_subtree(client, "root")

    assert client.read_run_id == "root"
    assert client.load_child_runs is True
    assert [run["id"] for run in runs] == ["root", "child", "grandchild"]
