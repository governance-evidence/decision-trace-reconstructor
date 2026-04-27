"""Argparse builder for the Generic JSONL ingest adapter."""

from __future__ import annotations

import argparse
from pathlib import Path

from ...cli.ingest_common import (
    _add_actor_override_argument,
    _add_architecture_argument,
    _add_out_argument,
    _add_scenario_id_argument,
    _add_stack_tier_argument,
)
from .cli_handler import _cmd_ingest_generic_jsonl


def register_ingest_parser(
    p_ingest_sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_generic_jsonl = p_ingest_sub.add_parser(
        "generic-jsonl",
        help="Generic JSONL fallback adapter for custom agent logs.",
    )
    p_generic_jsonl_src = p_generic_jsonl.add_mutually_exclusive_group(required=True)
    p_generic_jsonl_src.add_argument(
        "--from-file",
        type=Path,
        help="Read Generic JSONL records from a local line-delimited JSON export.",
    )
    p_generic_jsonl_src.add_argument(
        "--from-stdin",
        action="store_true",
        help="Read Generic JSONL records from stdin.",
    )
    p_generic_jsonl.add_argument(
        "--mapping",
        type=Path,
        required=True,
        help="Path to the Generic JSONL mapping config (YAML or JSON).",
    )
    _add_scenario_id_argument(p_generic_jsonl, "generic_jsonl_ingest")
    _add_architecture_argument(
        p_generic_jsonl,
        default=None,
        help_text="Override the mapping's architecture declaration.",
    )
    _add_stack_tier_argument(
        p_generic_jsonl,
        default=None,
        choices=("within_stack", "cross_stack", "human"),
        help_text="Override the mapping's default stack tier when records do not carry one.",
    )
    p_generic_jsonl.add_argument(
        "--strict-unknown-kinds",
        action="store_true",
        help="Fail instead of skipping when a record kind is absent from kind_map.",
    )
    p_generic_jsonl.add_argument(
        "--redact-fields",
        type=str,
        default="",
        help="Comma-separated field paths to redact in emitted payloads.",
    )
    _add_actor_override_argument(
        p_generic_jsonl,
        "Force a single actor_id for all emitted fragments.",
    )
    _add_out_argument(p_generic_jsonl)
    p_generic_jsonl.set_defaults(func=_cmd_ingest_generic_jsonl)
