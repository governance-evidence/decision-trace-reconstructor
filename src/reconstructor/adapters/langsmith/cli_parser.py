"""Argparse builder for the LangSmith ingest adapter."""

from __future__ import annotations

import argparse
from pathlib import Path

from ...cli.ingest_common import (
    _add_actor_override_argument,
    _add_architecture_argument,
    _add_out_argument,
    _add_scenario_id_argument,
    _add_stack_tier_argument,
    _add_state_mutation_tools_argument,
)
from .cli_handler import _cmd_ingest_langsmith


def register_ingest_parser(
    p_ingest_sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_ls = p_ingest_sub.add_parser(
        "langsmith",
        help="LangSmith / LangGraph trace adapter.",
    )
    src_group = p_ls.add_mutually_exclusive_group(required=True)
    src_group.add_argument(
        "--from-file",
        type=Path,
        help="Read LangSmith runs from a local JSON file (offline; no SDK needed).",
    )
    src_group.add_argument(
        "--trace-id",
        type=str,
        help="LangSmith trace UUID to fetch (requires [langsmith] extra).",
    )
    src_group.add_argument(
        "--run-id",
        type=str,
        help="LangSmith root run UUID to fetch (with descendants).",
    )
    _add_scenario_id_argument(p_ls, "langsmith_ingest")
    _add_architecture_argument(
        p_ls,
        default="single_agent",
        help_text="Architecture label for the manifest (default: single_agent).",
    )
    _add_stack_tier_argument(
        p_ls,
        default="within_stack",
        help_text="Default stack tier for fragments (default: within_stack).",
    )
    _add_state_mutation_tools_argument(
        p_ls,
        (
            "Regex matched against tool names; matching tool calls produce a "
            "state_mutation fragment alongside the tool_call. Example: "
            "'(write|exec|drop|delete|update|insert|push|publish)'."
        ),
    )
    _add_actor_override_argument(
        p_ls,
        "Force a single actor_id for the whole trace (default: derive per run).",
    )
    p_ls.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="LangSmith API key (default: from LANGSMITH_API_KEY env var).",
    )
    p_ls.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="LangSmith API URL (default: from LANGCHAIN_ENDPOINT env var).",
    )
    p_ls.add_argument(
        "--project",
        type=str,
        default=None,
        help="LangSmith project name (used with --trace-id in some tenancies).",
    )
    _add_out_argument(p_ls)
    p_ls.set_defaults(func=_cmd_ingest_langsmith)
