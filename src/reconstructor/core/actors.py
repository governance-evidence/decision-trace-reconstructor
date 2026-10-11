"""Descriptive producer roles, separated from action attribution."""

from __future__ import annotations

from .fragment import ActorRole, Fragment, FragmentKind


def actor_inventory(fragments: list[Fragment]) -> dict[str, list[str]]:
    roles: dict[str, set[str]] = {}
    for fragment in fragments:
        roles.setdefault(fragment.actor_id, set()).add(fragment.actor_role.value)
    agent_ids = {f.actor_id for f in fragments if f.actor_role == ActorRole.AGENT}
    inferred = {
        f.actor_id
        for f in fragments
        if roles[f.actor_id] == {ActorRole.UNKNOWN.value}
        and f.kind in (FragmentKind.MODEL_GENERATION, FragmentKind.TOOL_CALL)
    }
    return dict(
        record_producers=sorted(roles),
        declared_agents=sorted(agent_ids),
        inferred_action_or_model_actors=sorted(inferred),
        action_issuers=sorted({f.actor_id for f in fragments if f.kind == FragmentKind.TOOL_CALL}),
        role_conflicts=sorted(
            k for k, v in roles.items() if len(v - {ActorRole.UNKNOWN.value}) > 1
        ),
    )
