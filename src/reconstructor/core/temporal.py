"""Temporal ordering of fragments.

Stage 2 of the pipeline. Given a set of fragments, produce a causally
ordered list. Order is established from explicit timestamps plus
parent_trace_id edges where available.
"""

from __future__ import annotations

from .fragment import Fragment


def order_fragments(fragments: list[Fragment]) -> list[Fragment]:
    """Return fragments in canonical order.

    Primary key: timestamp. Parent-trace edges constrain the order so a known
    parent is emitted before its children even when clocks disagree. Cycles or
    otherwise unsatisfiable parent links are broken deterministically by the
    timestamp/fragment_id order.
    """
    remaining = sorted(fragments, key=lambda f: (f.timestamp, f.fragment_id))
    remaining_ids = {f.fragment_id for f in remaining}
    ordered: list[Fragment] = []

    while remaining:
        for index, frag in enumerate(remaining):
            if frag.parent_trace_id is None or frag.parent_trace_id not in remaining_ids:
                ordered.append(remaining.pop(index))
                remaining_ids.discard(frag.fragment_id)
                break
        else:
            frag = remaining.pop(0)
            ordered.append(frag)
            remaining_ids.discard(frag.fragment_id)

    return ordered


def causal_edges(fragments: list[Fragment]) -> dict[str, list[str]]:
    """Return a map from fragment_id to its children.

    Children are fragments whose parent_trace_id equals this fragment's id.
    Used for cross-service causal reconstruction.
    """
    children: dict[str, list[str]] = {f.fragment_id: [] for f in fragments}
    for f in fragments:
        if f.parent_trace_id and f.parent_trace_id in children:
            children[f.parent_trace_id].append(f.fragment_id)
    return children
