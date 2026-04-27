"""Shared Bedrock fragment helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ...core.fragment import Fragment, FragmentKind, StackTier


def _fragment(
    fragment_id: str,
    kind: FragmentKind,
    *,
    timestamp: float,
    stack_tier: StackTier,
    actor_id: str,
    parent_trace_id: str | None,
    decision_id_hint: str | None,
    payload: dict[str, Any],
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        timestamp=timestamp,
        kind=kind,
        stack_tier=stack_tier,
        actor_id=actor_id,
        parent_trace_id=parent_trace_id,
        decision_id_hint=decision_id_hint,
        payload=payload,
    )


def _fragment_id(session_id: str, suffix: str, timestamp: float | None = None) -> str:
    short = session_id.replace("-", "")[:10] or "unknown"
    if timestamp is None:
        return f"bedrock_{short}_{suffix}"
    millis = int(timestamp * 1000)
    return f"bedrock_{short}_{suffix}_{millis}"


def _content_field(content: Any, store_content: bool) -> Any:
    if content is None:
        return None
    if store_content:
        return content
    encoded = content if isinstance(content, str) else json.dumps(content, sort_keys=True)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return {"sha256": digest, "length": len(encoded)}
