"""Architecture inference for Pydantic AI runs."""

from __future__ import annotations

from typing import Any

from .common import PydanticAIIngestOptions


def _infer_architecture(runs: list[dict[str, Any]], opts: PydanticAIIngestOptions) -> str:
    if not opts.auto_architecture:
        return opts.architecture
    agent_names = {str(run["agent_name"]) for run in runs if run.get("agent_name")}
    return "multi_agent" if len(agent_names) >= 2 else "single_agent"
