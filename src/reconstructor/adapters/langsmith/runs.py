"""LangSmith run normalisation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .common import _to_epoch

if TYPE_CHECKING:
    from langsmith.schemas import Run


def _normalise_run(run: dict[str, Any] | Any) -> dict[str, Any]:
    """Bring either dict or ``Run`` into a canonical dict form for mapping.

    Adds a ``_ts`` epoch float so callers can sort by it without re-parsing.
    """
    if isinstance(run, dict):
        d = dict(run)
    else:
        d = _run_obj_to_dict(run)
    d["_ts"] = _to_epoch(d.get("start_time"))
    return d


def _run_obj_to_dict(run: Run) -> dict[str, Any]:
    """Serialise a ``langsmith.schemas.Run`` Pydantic object into a plain dict.

    We deliberately avoid ``run.model_dump()`` for the whole object because
    it eagerly serialises children; we want the descendant traversal to be
    explicit. UUID fields are converted to strings for JSON friendliness.
    """
    return {
        "id": str(run.id),
        "name": run.name,
        "run_type": run.run_type,
        "start_time": run.start_time,
        "end_time": run.end_time,
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
        "trace_id": str(run.trace_id),
        "inputs": dict(run.inputs or {}),
        "outputs": dict(run.outputs or {}),
        "error": run.error,
        "tags": list(run.tags or []),
        "extra": dict(run.extra or {}),
        "events": list(run.events or []),
        "session_id": str(run.session_id) if run.session_id else None,
        "status": run.status,
    }
