"""Pydantic AI tool, state, and takeover fragment builders."""

from __future__ import annotations

import re
from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier
from .common import PydanticAIIngestOptions, _matches
from .fragment_common import _fragment


def _tool_fragment(
    run_payload: dict[str, Any],
    tool_record: dict[str, Any],
    tool_return: dict[str, Any] | None,
    opts: PydanticAIIngestOptions,
) -> Fragment:
    payload = {
        "tool_name": tool_record["tool_name"],
        "args": dict(tool_record["args"]),
    }
    if tool_return is not None:
        payload["result"] = tool_return.get("content")
    else:
        payload["incomplete"] = True
    return _fragment(
        run_payload,
        fragment_id=f"pydantic_ai_{run_payload['run_id']}_{tool_record['tool_name']}_{int(tool_record['timestamp'] * 1000)}_tool",
        timestamp=float(tool_record["timestamp"]),
        kind=FragmentKind.TOOL_CALL,
        stack_tier=_tool_stack_tier(tool_record, opts),
        actor_id=tool_record["tool_name"],
        payload=payload,
    )


def _state_fragment(
    run_payload: dict[str, Any],
    tool_record: dict[str, Any],
    opts: PydanticAIIngestOptions,
) -> Fragment:
    return _fragment(
        run_payload,
        fragment_id=f"pydantic_ai_{run_payload['run_id']}_{tool_record['tool_name']}_{int(tool_record['timestamp'] * 1000)}_state",
        timestamp=float(tool_record["timestamp"]) + 0.0001,
        kind=FragmentKind.STATE_MUTATION,
        stack_tier=_tool_stack_tier(tool_record, opts),
        actor_id=tool_record["tool_name"],
        payload={"tool_name": tool_record["tool_name"], "args": dict(tool_record["args"])},
    )


def _takeover_fragment(
    run_payload: dict[str, Any],
    tool_record: dict[str, Any],
    tool_return: dict[str, Any],
    opts: PydanticAIIngestOptions,
) -> Fragment | None:
    tool_def = tool_record.get("tool_def") or {}
    is_takeover = bool(tool_def.get("is_takeover")) or _matches(
        tool_record["tool_name"], opts.takeover_tool_pattern
    )
    if not is_takeover:
        return None
    content = str(tool_return.get("content") or "")
    approved = bool(opts.human_approval_pattern and re.search(opts.human_approval_pattern, content))
    kind = FragmentKind.HUMAN_APPROVAL if approved else FragmentKind.HUMAN_REJECTION
    return _fragment(
        run_payload,
        fragment_id=f"pydantic_ai_{run_payload['run_id']}_{tool_record['tool_name']}_{int(tool_record['timestamp'] * 1000)}_takeover",
        timestamp=float(tool_record["timestamp"]) + 0.0002,
        kind=kind,
        stack_tier=StackTier.HUMAN,
        actor_id=tool_record["tool_name"],
        payload={"tool_name": tool_record["tool_name"], "content": content},
    )


def _tool_stack_tier(tool_record: dict[str, Any], opts: PydanticAIIngestOptions) -> StackTier:
    if _matches(tool_record["tool_name"], opts.cross_stack_tools_pattern):
        return StackTier.CROSS_STACK
    if _schema_has_external_url((tool_record.get("tool_def") or {}).get("params_schema")):
        return StackTier.CROSS_STACK
    return opts.stack_tier


def _schema_has_external_url(schema: Any) -> bool:
    if isinstance(schema, str):
        return bool(re.search(r"https?://", schema))
    if isinstance(schema, dict):
        return any(_schema_has_external_url(value) for value in schema.values())
    if isinstance(schema, list):
        return any(_schema_has_external_url(item) for item in schema)
    return False
