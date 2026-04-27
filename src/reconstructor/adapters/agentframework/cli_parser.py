"""Argparse builder for the Agent Framework ingest adapter."""

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
from .cli_handler import _cmd_ingest_agentframework


def register_ingest_parser(
    p_ingest_sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_agentframework = p_ingest_sub.add_parser(
        "agentframework",
        help="Microsoft Agent Framework / AutoGen offline event adapter.",
    )
    _add_required_from_file_argument(
        p_agentframework,
        "Read Agent Framework MessageRecord events from a local JSON or JSONL export.",
    )
    _add_scenario_id_argument(p_agentframework, "agentframework_ingest")
    _add_architecture_argument(
        p_agentframework,
        default="single_agent",
        help_text="Architecture label for the manifest when auto-detection is disabled.",
    )
    _add_auto_architecture_argument(
        p_agentframework,
        "Infer architecture from speaker selection, agent diversity, and human proxy events.",
    )
    _add_stack_tier_argument(
        p_agentframework,
        default="within_stack",
        help_text="Default stack tier for fragments (default: within_stack).",
    )
    p_agentframework.add_argument(
        "--cross-stack-tools",
        type=str,
        default=None,
        help="Regex matched against tool names that should be treated as cross-stack.",
    )
    _add_state_mutation_tools_argument(
        p_agentframework,
        "Regex matched against tool names to emit paired state_mutation fragments.",
    )
    _add_actor_override_argument(
        p_agentframework,
        "Force a single actor_id for the whole trace.",
    )
    p_agentframework.add_argument(
        "--runtime",
        type=str,
        default=None,
        choices=("single_threaded", "grpc"),
        help="Override runtime inference for stack-tier elevation.",
    )
    p_agentframework.add_argument(
        "--topic-filter",
        type=str,
        default=None,
        help="Only ingest events whose topic matches this regex.",
    )
    _add_out_argument(p_agentframework)
    p_agentframework.set_defaults(func=_cmd_ingest_agentframework)
