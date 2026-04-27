"""Pydantic AI run and model fragment builders."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from .common import PydanticAIIngestOptions
from .fragment_common import _fragment


def _config_fragment(
    run_payload: dict[str, Any],
    actor_id: str,
    opts: PydanticAIIngestOptions,
) -> Fragment:
    return _fragment(
        run_payload,
        fragment_id=f"pydantic_ai_{run_payload['run_id']}_config",
        timestamp=float(run_payload["ts_start"]),
        kind=FragmentKind.CONFIG_SNAPSHOT,
        stack_tier=opts.stack_tier,
        actor_id=actor_id,
        payload={
            "agent_name": run_payload["agent_name"],
            "model": run_payload["model"],
            "deps_type": run_payload["deps_type"],
            "result_type": run_payload["result_type"],
            "result_schema": run_payload["result_schema"],
            "tools": run_payload["tools"],
        },
    )


def _result_fragment(
    run_payload: dict[str, Any],
    actor_id: str,
    opts: PydanticAIIngestOptions,
) -> Fragment:
    return _fragment(
        run_payload,
        fragment_id=f"pydantic_ai_{run_payload['run_id']}_result",
        timestamp=float(run_payload["ts_end"] or run_payload["ts_start"]),
        kind=FragmentKind.AGENT_MESSAGE,
        stack_tier=opts.stack_tier,
        actor_id=actor_id,
        payload={"result": run_payload["result"], "usage": run_payload["usage"]},
    )


def _model_fragment(
    run_payload: dict[str, Any],
    message: dict[str, Any],
    actor_id: str,
    opts: PydanticAIIngestOptions,
    timestamp: float,
) -> Fragment:
    return _fragment(
        run_payload,
        fragment_id=f"pydantic_ai_{run_payload['run_id']}_{message['message_id']}_model",
        timestamp=timestamp,
        kind=FragmentKind.MODEL_GENERATION,
        stack_tier=opts.stack_tier,
        actor_id=actor_id,
        payload={
            "model_id": message.get("model_name") or run_payload["model"],
            "internal_reasoning": "opaque",
            "kind_metadata": message.get("kind_metadata") or {},
        },
    )
