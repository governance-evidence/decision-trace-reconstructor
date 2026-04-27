"""Agent Framework event-to-manifest conversion pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ...core.fragment import Fragment
from ...core.manifest import manifest_dict
from .architecture import _infer_architecture
from .common import AgentFrameworkIngestOptions, _event_allowed
from .events import _normalise_event
from .handlers import _flush_pending, _handle_event
from .state import _new_state


def events_to_fragments(
    events: Iterable[dict[str, Any] | Any],
    opts: AgentFrameworkIngestOptions | None = None,
) -> list[Fragment]:
    cfg = opts or AgentFrameworkIngestOptions()
    normalised = [_normalise_event(event, index) for index, event in enumerate(events)]
    normalised.sort(key=lambda event: (event["timestamp"], event["_index"], event["message_id"]))

    state = _new_state(cfg)
    for event in normalised:
        _handle_event(state, event)

    _flush_pending(state)
    state.out.sort(key=lambda fragment: (fragment.timestamp, fragment.fragment_id))
    return state.out


def events_to_manifest(
    events: Iterable[dict[str, Any] | Any],
    scenario_id: str,
    opts: AgentFrameworkIngestOptions | None = None,
) -> dict[str, Any]:
    cfg = opts or AgentFrameworkIngestOptions()
    normalised = [_normalise_event(event, index) for index, event in enumerate(events)]
    if cfg.topic_filter:
        normalised = [event for event in normalised if _event_allowed(event, cfg)]
    fragments = events_to_fragments(normalised, cfg)
    architecture = _infer_architecture(normalised, cfg)
    return manifest_dict(
        scenario_id=scenario_id,
        architecture=architecture,
        stack_tier=cfg.stack_tier,
        fragments=fragments,
    )


__all__ = ["events_to_fragments", "events_to_manifest"]
