"""Evidence fragment abstraction.

A Fragment is a single typed record of something that happened in an agent
execution: a tool call, a model generation, an operator approval, a policy
snapshot, or a system-configuration marker. Fragments are the input to the
reconstruction pipeline.

JSON serialisation is symmetric: ``Fragment.to_dict()`` produces the wire
form consumed by ``Fragment.from_dict()``. The wire form is also the schema
used by ``examples/`` and the ``decision-trace reconstruct`` CLI command.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FragmentKind(str, Enum):
    """Fragment type taxonomy."""

    TOOL_CALL = "tool_call"
    MODEL_GENERATION = "model_generation"
    HUMAN_APPROVAL = "human_approval"
    HUMAN_REJECTION = "human_rejection"
    POLICY_SNAPSHOT = "policy_snapshot"
    CONFIG_SNAPSHOT = "config_snapshot"
    AGENT_MESSAGE = "agent_message"
    RETRIEVAL_RESULT = "retrieval_result"
    STATE_MUTATION = "state_mutation"
    ERROR = "error"


class StackTier(str, Enum):
    """Where the fragment originated."""

    WITHIN_STACK = "within_stack"
    CROSS_STACK = "cross_stack"
    HUMAN = "human"


@dataclass(frozen=True)
class Fragment:
    """A single piece of evidence about an agent execution step.

    Each fragment has a stable identifier, a timestamp, a kind, and an
    origin stack tier that determines whether it carries governance-grade
    telemetry or is a cross-stack opaque observation.
    """

    fragment_id: str
    timestamp: float  # Unix epoch seconds
    kind: FragmentKind
    stack_tier: StackTier
    actor_id: str  # agent id, operator id, or system id
    payload: dict[str, Any] = field(default_factory=dict)
    parent_trace_id: str | None = None
    decision_id_hint: str | None = None  # scenario-provided decision association

    def is_tool_call(self) -> bool:
        return self.kind == FragmentKind.TOOL_CALL

    def is_human_intervention(self) -> bool:
        return self.kind in (FragmentKind.HUMAN_APPROVAL, FragmentKind.HUMAN_REJECTION)

    def is_policy_trigger(self) -> bool:
        return self.kind == FragmentKind.POLICY_SNAPSHOT and bool(
            self.payload.get("constraint_activated", False)
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dict (round-trip-compatible with from_dict)."""
        return {
            "fragment_id": self.fragment_id,
            "timestamp": self.timestamp,
            "kind": self.kind.value,
            "stack_tier": self.stack_tier.value,
            "actor_id": self.actor_id,
            "payload": dict(self.payload),
            "parent_trace_id": self.parent_trace_id,
            "decision_id_hint": self.decision_id_hint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Fragment:
        """Construct a Fragment from a JSON-loaded dict.

        Required keys: fragment_id, timestamp, kind, stack_tier, actor_id.
        Optional: payload (default empty), parent_trace_id, decision_id_hint.

        Raises:
            ValueError: on unknown FragmentKind / StackTier values.
            KeyError:   on missing required keys.
        """
        _require_fragment_keys(data)
        return cls(
            fragment_id=str(data["fragment_id"]),
            timestamp=float(data["timestamp"]),
            kind=_parse_fragment_kind(data["kind"]),
            stack_tier=_parse_stack_tier(data["stack_tier"]),
            actor_id=str(data["actor_id"]),
            payload=dict(data.get("payload", {})),
            parent_trace_id=data.get("parent_trace_id"),
            decision_id_hint=data.get("decision_id_hint"),
        )


def _require_fragment_keys(data: dict[str, Any]) -> None:
    required = ("fragment_id", "timestamp", "kind", "stack_tier", "actor_id")
    for key in required:
        if key not in data:
            raise KeyError(f"Fragment.from_dict: missing required key {key!r}")


def _parse_fragment_kind(value: Any) -> FragmentKind:
    try:
        return FragmentKind(value)
    except ValueError as exc:
        valid = ", ".join(sorted(k.value for k in FragmentKind))
        raise ValueError(
            f"Fragment.from_dict: unknown kind {value!r}. Expected one of: {valid}"
        ) from exc


def _parse_stack_tier(value: Any) -> StackTier:
    try:
        return StackTier(value)
    except ValueError as exc:
        valid = ", ".join(sorted(t.value for t in StackTier))
        raise ValueError(
            f"Fragment.from_dict: unknown stack_tier {value!r}. Expected one of: {valid}"
        ) from exc
