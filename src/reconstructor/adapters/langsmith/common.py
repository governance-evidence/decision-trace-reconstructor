"""Shared LangSmith adapter types and low-level helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ...core.fragment import StackTier


@dataclass(frozen=True)
class LangSmithIngestOptions:
    """Operator-supplied parameters that pin scenario semantics.

    LangSmith does not carry architecture or stack-tier hints by itself, so
    these are required from the caller. They flow through to the resulting
    fragments-manifest and to the the reconstructor mapper.
    """

    architecture: str = "single_agent"
    stack_tier: StackTier = StackTier.WITHIN_STACK

    # Skip noisy internal LangChain run types that carry no governance signal.
    # Override (set to ``()``) if you want a maximally faithful trace.
    skip_run_types: tuple[str, ...] = ("parser", "embedding")

    # Regex matched against run names / metadata to detect a LangGraph
    # human-in-the-loop node. Default catches ``human``, ``approval``, ``hitl``
    # in case-insensitive mode.
    human_node_pattern: str = r"(human|approval|hitl)"

    # Regex matched against tool names to flag a tool call as
    # state-mutating. Default ``None`` disables the heuristic; operators with
    # known destructive tool names should set e.g. ``r"(write|exec|drop|
    # delete|update|insert|push|publish)"``.
    state_mutation_tool_pattern: str | None = None

    # Tags whose presence on a run elevates that run to ``policy_snapshot`` or
    # ``config_snapshot`` -- the two fragment kinds LangSmith does not
    # natively carry.
    policy_snapshot_tags: tuple[str, ...] = ("policy_snapshot", "policy")
    config_snapshot_tags: tuple[str, ...] = ("config_snapshot", "config")

    # Optional override for actor_id derivation. By default we look at, in
    # order: extra.metadata.langgraph_node, extra.metadata.agent_name,
    # run.name. Set to a fixed string to force a single actor for the whole
    # trace (useful for single-agent runs where the LangGraph node names are
    # noisy implementation details rather than governance-relevant actors).
    actor_override: str | None = None

    # Drop-in defaults for properties LangSmith never exposes; harmless
    # ``parent_trace_id`` propagation and explicit unknown defaults.
    extra_payload_keys: tuple[str, ...] = field(default_factory=tuple)


def _to_epoch(ts: Any) -> float:
    """Coerce datetime / ISO-8601 string / float to Unix-epoch seconds."""
    if ts is None:
        return 0.0
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, datetime):
        return ts.timestamp()
    if isinstance(ts, str):
        # ISO 8601 with optional trailing Z or timezone.
        # Python 3.11+: fromisoformat handles "Z" suffix natively.
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    raise TypeError(f"Unsupported timestamp type: {type(ts)!r}")
