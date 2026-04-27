"""Argparse builder for the OpenAI Agents ingest adapter."""

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
from .cli_handler import _cmd_ingest_openai_agents


def register_ingest_parser(
    p_ingest_sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_openai = p_ingest_sub.add_parser(
        "openai-agents",
        help="OpenAI Agents SDK offline trace adapter.",
    )
    _add_required_from_file_argument(
        p_openai,
        "Read OpenAI Agents traces from a local JSON or JSONL export.",
    )
    _add_scenario_id_argument(
        p_openai,
        "openai_agents_ingest",
        "Scenario id or prefix to embed in the manifest (default: openai_agents_ingest).",
    )
    _add_architecture_argument(
        p_openai,
        default="single_agent",
        help_text="Architecture label for the manifest (default: single_agent).",
    )
    _add_auto_architecture_argument(
        p_openai,
        "Infer multi-agent architecture from handoff spans and agent-name diversity.",
    )
    _add_stack_tier_argument(
        p_openai,
        default="within_stack",
        help_text="Default stack tier for fragments (default: within_stack).",
    )
    p_openai.add_argument(
        "--cross-stack-tools",
        type=str,
        default="",
        help="Comma-separated function tool names that should be treated as cross-stack.",
    )
    _add_state_mutation_tools_argument(
        p_openai,
        "Regex matched against function tool names to emit state_mutation fragments.",
    )
    _add_actor_override_argument(p_openai, "Force a single actor_id for the whole trace.")
    p_openai.add_argument(
        "--store-reasoning",
        action="store_true",
        help="Keep reasoning summaries from response spans instead of redacting them.",
    )
    p_openai.add_argument(
        "--group-into-scenarios",
        action="store_true",
        help="Merge traces with the same group_id before emitting manifests.",
    )
    _add_out_argument(
        p_openai,
        "Output fragments-manifest path; use a directory when multiple manifests are emitted.",
    )
    p_openai.set_defaults(func=_cmd_ingest_openai_agents)
