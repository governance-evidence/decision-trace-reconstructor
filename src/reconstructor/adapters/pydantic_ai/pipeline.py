"""Pydantic AI run-to-manifest conversion pipeline."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment
from ...core.manifest import manifest_dict
from .architecture import _infer_architecture
from .common import PydanticAIIngestOptions
from .events import _normalise_run
from .fragments import _config_fragment, _result_fragment
from .handlers import _flush_pending_tools, _handle_message
from .state import _new_run_state


def runs_to_fragments(
    runs: list[dict[str, Any]] | Any,
    opts: PydanticAIIngestOptions | None = None,
) -> list[Fragment]:
    cfg = opts or PydanticAIIngestOptions()
    out: list[Fragment] = []
    for run_payload in _normalise_runs(runs):
        out.extend(_run_to_fragments(run_payload, cfg))
    out.sort(key=lambda fragment: (fragment.timestamp, fragment.fragment_id))
    return out


def runs_to_manifest(
    runs: list[dict[str, Any]] | Any,
    scenario_id: str,
    opts: PydanticAIIngestOptions | None = None,
) -> dict[str, Any]:
    cfg = opts or PydanticAIIngestOptions()
    normalised = _normalise_runs(runs)
    fragments = runs_to_fragments(normalised, cfg)
    architecture = _infer_architecture(normalised, cfg)
    return manifest_dict(
        scenario_id=scenario_id,
        architecture=architecture,
        stack_tier=cfg.stack_tier,
        fragments=fragments,
    )


def _normalise_runs(runs: list[dict[str, Any]] | Any) -> list[dict[str, Any]]:
    return [
        _normalise_run(run_payload, index)
        for index, run_payload in enumerate(runs if isinstance(runs, list) else [runs])
    ]


def _run_to_fragments(run_payload: dict[str, Any], opts: PydanticAIIngestOptions) -> list[Fragment]:
    state = _new_run_state(run_payload, opts)
    state.out.append(_config_fragment(run_payload, state.actor_id, opts))

    for message_index, message in enumerate(run_payload["messages"]):
        _handle_message(state, message, message_index)

    _flush_pending_tools(state)
    if run_payload.get("result") is not None:
        state.out.append(_result_fragment(run_payload, state.actor_id, opts))
    return state.out
