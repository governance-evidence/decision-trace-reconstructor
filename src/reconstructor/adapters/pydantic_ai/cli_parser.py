"""Argparse builder for the Pydantic AI ingest adapter."""

from __future__ import annotations

import argparse

from ...cli.ingest_common import (
    _add_actor_override_argument,
    _add_architecture_argument,
    _add_auto_architecture_argument,
    _add_out_argument,
    _add_required_from_file_argument,
    _add_scenario_id_argument,
    _add_stack_tier_argument,
    _add_state_mutation_tools_argument,
)
from .cli_handler import _cmd_ingest_pydantic_ai


def register_ingest_parser(
    p_ingest_sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_pydantic_ai = p_ingest_sub.add_parser(
        "pydantic-ai",
        help="Pydantic AI offline run adapter.",
    )
    _add_required_from_file_argument(
        p_pydantic_ai,
        "Read Pydantic AI run records from a local JSON or JSONL export.",
    )
    _add_scenario_id_argument(p_pydantic_ai, "pydantic_ai_ingest")
    _add_architecture_argument(
        p_pydantic_ai,
        default="single_agent",
        help_text="Architecture label for the manifest when auto-detection is disabled.",
    )
    _add_auto_architecture_argument(
        p_pydantic_ai,
        "Infer multi-agent architecture from distinct agent_name values across runs.",
    )
    _add_stack_tier_argument(
        p_pydantic_ai,
        default="within_stack",
        help_text="Default stack tier for fragments (default: within_stack).",
    )
    p_pydantic_ai.add_argument(
        "--cross-stack-tools",
        type=str,
        default=None,
        help="Regex matched against tool names that should be treated as cross-stack.",
    )
    _add_state_mutation_tools_argument(
        p_pydantic_ai,
        "Regex matched against tool names to emit paired state_mutation fragments.",
    )
    p_pydantic_ai.add_argument(
        "--takeover-tool-pattern",
        type=str,
        default=None,
        help="Regex matched against takeover-capable tool names for HITL approval/rejection mapping.",
    )
    p_pydantic_ai.add_argument(
        "--human-approval-pattern",
        type=str,
        default=None,
        help="Regex matched against takeover tool return content to emit human_approval.",
    )
    p_pydantic_ai.add_argument(
        "--emit-system-prompt",
        action="store_true",
        help="Emit system prompt parts as config_snapshot fragments.",
    )
    _add_actor_override_argument(p_pydantic_ai, "Force a single actor_id for the whole run.")
    _add_out_argument(p_pydantic_ai)
    p_pydantic_ai.set_defaults(func=_cmd_ingest_pydantic_ai)
