"""LangSmith run classification predicates."""

from __future__ import annotations

import re
from typing import Any

from .common import LangSmithIngestOptions


def _is_human_node(run: dict[str, Any], opts: LangSmithIngestOptions) -> bool:
    pattern = re.compile(opts.human_node_pattern, re.IGNORECASE)
    name = run.get("name") or ""
    if pattern.search(name):
        return True
    extra = run.get("extra") or {}
    metadata = extra.get("metadata") if isinstance(extra, dict) else None
    if isinstance(metadata, dict):
        node = metadata.get("langgraph_node")
        if isinstance(node, str) and pattern.search(node):
            return True
    tags = run.get("tags") or []
    return any(pattern.search(t) for t in tags)


def _has_any_tag(run: dict[str, Any], wanted: tuple[str, ...]) -> bool:
    tags = run.get("tags") or []
    return any(t in tags for t in wanted)


def _is_state_mutating_tool(tool_name: str | None, opts: LangSmithIngestOptions) -> bool:
    if not tool_name or not opts.state_mutation_tool_pattern:
        return False
    return re.search(opts.state_mutation_tool_pattern, tool_name, re.IGNORECASE) is not None
