"""LangSmith network fetch helpers.

These functions require the optional ``langsmith`` SDK only at call time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .runs import _run_obj_to_dict

if TYPE_CHECKING:
    from langsmith import Client
    from langsmith.schemas import Run


def fetch_trace(
    client: Client,
    trace_id: str,
    *,
    project_name: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch all runs in a trace from LangSmith and return them as dicts.

    Args:
        client: A configured ``langsmith.Client`` instance.
        trace_id: The LangSmith trace id (UUID).
        project_name: Optional project filter; required by some LangSmith
            tenancies for cross-project queries.

    Returns:
        List of run dicts (one per run in the trace), unordered.
    """
    runs = client.list_runs(
        project_name=project_name,
        trace=trace_id,
    )
    return [_run_obj_to_dict(r) for r in runs]


def fetch_run_subtree(
    client: Client,
    root_run_id: str,
) -> list[dict[str, Any]]:
    """Fetch a single run plus all its descendants (transitive children)."""
    root = client.read_run(root_run_id, load_child_runs=True)
    out: list[dict[str, Any]] = []
    stack: list[Run] = [root]
    while stack:
        node = stack.pop()
        out.append(_run_obj_to_dict(node))
        for child in node.child_runs or []:
            stack.append(child)
    return out
