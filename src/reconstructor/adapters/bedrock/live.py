"""Live AWS readers for Bedrock AgentCore ingest."""

from __future__ import annotations

import importlib
from typing import Any

from .live_memory import _attach_memory_contents
from .live_pagination import _collect_paginated
from .normalize import normalise_bedrock_input


def load_sessions_cloudwatch(
    log_group_name: str,
    *,
    aws_profile: str | None = None,
    region: str | None = None,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    session_id: str | None = None,
    agent_id: str | None = None,
    memory_id: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch Bedrock CloudWatch events live via boto3 and normalize them.

    The live path intentionally reuses the same CloudWatch-event normalization
    logic as offline JSON/JSONL exports so the mapping surface stays identical.
    """
    events = fetch_cloudwatch_events(
        log_group_name,
        aws_profile=aws_profile,
        region=region,
        start_time_ms=start_time_ms,
        end_time_ms=end_time_ms,
    )
    sessions = normalise_bedrock_input({"events": events})
    if session_id is not None:
        sessions = [session for session in sessions if session["session_id"] == session_id]
    if agent_id is not None:
        sessions = [session for session in sessions if session.get("agent_id") == agent_id]
    if (session_id is not None or agent_id is not None) and not sessions:
        detail = session_id if session_id is not None else agent_id
        raise ValueError(f"No Bedrock sessions matched the requested selector: {detail}")
    if memory_id is not None:
        if not sessions:
            raise ValueError("Cannot attach Bedrock memory without at least one matching session")
        exemplar = sessions[0]
        agent_ref = exemplar.get("agent_id")
        alias_ref = exemplar.get("agent_alias_id")
        if not agent_ref or not alias_ref:
            raise ValueError("Bedrock memory fetch requires agent_id and agent_alias_id")
        memory_contents = fetch_agent_memory_contents(
            str(agent_ref),
            str(alias_ref),
            memory_id,
            aws_profile=aws_profile,
            region=region,
        )
        sessions = _attach_memory_contents(sessions, memory_id, memory_contents)
    return sessions


def fetch_cloudwatch_events(
    log_group_name: str,
    *,
    aws_profile: str | None = None,
    region: str | None = None,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch raw CloudWatch log events from a Bedrock AgentCore log group."""
    boto3 = _import_boto3()

    session = boto3.session.Session(profile_name=aws_profile, region_name=region)
    client = session.client("logs")

    kwargs: dict[str, Any] = {"logGroupName": log_group_name}
    if start_time_ms is not None:
        kwargs["startTime"] = start_time_ms
    if end_time_ms is not None:
        kwargs["endTime"] = end_time_ms

    return _collect_paginated(client, "filter_log_events", "events", kwargs)


def fetch_agent_memory_contents(
    agent_id: str,
    agent_alias_id: str,
    memory_id: str,
    *,
    aws_profile: str | None = None,
    region: str | None = None,
    max_items: int = 1000,
) -> list[dict[str, Any]]:
    """Fetch Bedrock agent memory summaries via the read-only runtime API."""
    boto3 = _import_boto3()

    session = boto3.session.Session(profile_name=aws_profile, region_name=region)
    client = session.client("bedrock-agent-runtime")

    kwargs: dict[str, Any] = {
        "agentId": agent_id,
        "agentAliasId": agent_alias_id,
        "memoryId": memory_id,
        "memoryType": "SESSION_SUMMARY",
        "maxItems": max_items,
    }
    return _collect_paginated(client, "get_agent_memory", "memoryContents", kwargs)


def _import_boto3() -> Any:
    try:
        boto3 = importlib.import_module("boto3")
    except ImportError as exc:
        raise ImportError(
            "Bedrock live ingest requires the [bedrock] extra. "
            "Install with `pip install -e '.[bedrock]'`."
        ) from exc
    return boto3


__all__ = [
    "fetch_agent_memory_contents",
    "fetch_cloudwatch_events",
    "load_sessions_cloudwatch",
]
