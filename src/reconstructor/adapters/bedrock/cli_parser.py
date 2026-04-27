"""Argparse builder for the Bedrock ingest adapter."""

from __future__ import annotations

import argparse
from pathlib import Path

from ...cli.ingest_common import (
    _add_actor_override_argument,
    _add_architecture_argument,
    _add_auto_architecture_argument,
    _add_out_argument,
    _add_scenario_id_argument,
    _add_stack_tier_argument,
    _add_state_mutation_tools_argument,
)
from .cli_args import _add_bedrock_cloudwatch_options
from .cli_handler import _cmd_ingest_bedrock


def register_ingest_parser(
    p_ingest_sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_bedrock = p_ingest_sub.add_parser(
        "bedrock",
        help="AWS Bedrock AgentCore trace adapter (offline exports or live CloudWatch ingest).",
    )
    p_bedrock_src = p_bedrock.add_mutually_exclusive_group(required=True)
    p_bedrock_src.add_argument(
        "--from-file",
        type=Path,
        help="Read Bedrock AgentCore trace data from a local JSON or JSONL export.",
    )
    p_bedrock_src.add_argument(
        "--log-group",
        type=str,
        help="Fetch Bedrock AgentCore CloudWatch events live from the given log group.",
    )
    _add_scenario_id_argument(p_bedrock, "bedrock_ingest")
    _add_architecture_argument(
        p_bedrock,
        default="single_agent",
        help_text="Architecture label for the manifest (default: single_agent).",
    )
    _add_auto_architecture_argument(
        p_bedrock,
        "Infer multi-agent architecture from collaborator invocation blocks.",
    )
    _add_stack_tier_argument(
        p_bedrock,
        default="within_stack",
        help_text="Default stack tier for fragments (default: within_stack).",
    )
    p_bedrock.add_argument(
        "--cross-stack-action-groups",
        type=str,
        default="",
        help="Comma-separated actionGroup names that should be treated as cross-stack.",
    )
    _add_bedrock_cloudwatch_options(p_bedrock)
    _add_state_mutation_tools_argument(
        p_bedrock,
        "Regex matched against action-group tool names to emit state_mutation fragments.",
    )
    _add_actor_override_argument(p_bedrock, "Force a single actor_id for the whole session.")
    p_bedrock.add_argument(
        "--store-content",
        action="store_true",
        help="Keep raw prompt / response / tool content instead of hashed summaries.",
    )
    _add_out_argument(p_bedrock)
    p_bedrock.set_defaults(func=_cmd_ingest_bedrock)
