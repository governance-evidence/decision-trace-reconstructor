"""Core helper behavior tests."""

from __future__ import annotations

import pytest

from reconstructor.core.architecture import Architecture, coerce_architecture
from reconstructor.core.fragment import Fragment, FragmentKind, StackTier
from reconstructor.core.temporal import causal_edges, order_fragments


def _fragment(
    fragment_id: str,
    timestamp: float,
    parent_trace_id: str | None = None,
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        timestamp=timestamp,
        kind=FragmentKind.AGENT_MESSAGE,
        stack_tier=StackTier.WITHIN_STACK,
        actor_id="agent",
        payload={},
        parent_trace_id=parent_trace_id,
    )


def test_order_fragments_uses_timestamp_then_fragment_id() -> None:
    later = _fragment("z", 2.0)
    tie_b = _fragment("b", 1.0)
    tie_a = _fragment("a", 1.0)

    assert order_fragments([later, tie_b, tie_a]) == [tie_a, tie_b, later]


def test_order_fragments_emits_known_parent_before_child() -> None:
    parent = _fragment("parent", 2.0)
    child = _fragment("child", 1.0, parent_trace_id="parent")

    assert order_fragments([child, parent]) == [parent, child]


def test_order_fragments_keeps_timestamp_order_for_unblocked_fragments() -> None:
    parent = _fragment("parent", 3.0)
    child = _fragment("child", 1.0, parent_trace_id="parent")
    independent = _fragment("independent", 2.0)

    assert order_fragments([child, parent, independent]) == [independent, parent, child]


def test_order_fragments_breaks_cycles_deterministically() -> None:
    first = _fragment("a", 1.0, parent_trace_id="b")
    second = _fragment("b", 2.0, parent_trace_id="a")

    assert order_fragments([second, first]) == [first, second]


def test_causal_edges_ignores_missing_parents() -> None:
    root = _fragment("root", 1.0)
    child = _fragment("child", 2.0, parent_trace_id="root")
    orphan = _fragment("orphan", 3.0, parent_trace_id="missing")

    assert causal_edges([root, child, orphan]) == {
        "root": ["child"],
        "child": [],
        "orphan": [],
    }


def test_coerce_architecture_accepts_enum_and_rejects_unknown_values() -> None:
    assert coerce_architecture(Architecture.SINGLE_AGENT) is Architecture.SINGLE_AGENT
    assert coerce_architecture("multi_agent") is Architecture.MULTI_AGENT
    with pytest.raises(ValueError, match="unknown architecture 'unknown'"):
        coerce_architecture("unknown")


def test_fragment_from_dict_reports_invalid_wire_values() -> None:
    base = {
        "fragment_id": "f1",
        "timestamp": 1.0,
        "kind": "agent_message",
        "stack_tier": "within_stack",
        "actor_id": "agent",
    }

    with pytest.raises(ValueError, match="unknown kind 'bad_kind'"):
        Fragment.from_dict({**base, "kind": "bad_kind"})
    with pytest.raises(ValueError, match="unknown stack_tier 'bad_tier'"):
        Fragment.from_dict({**base, "stack_tier": "bad_tier"})
    with pytest.raises(KeyError, match="missing required key 'actor_id'"):
        Fragment.from_dict({key: value for key, value in base.items() if key != "actor_id"})
