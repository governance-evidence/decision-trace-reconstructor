"""CLI integration for the Anthropic adapter."""

from __future__ import annotations

import argparse
import json
import sys

from ...cli.ingest_common import (
    _add_actor_override_argument,
    _add_architecture_argument,
    _add_out_argument,
    _add_required_from_file_argument,
    _add_scenario_id_argument,
    _add_stack_tier_argument,
    _add_state_mutation_tools_argument,
)
from ...cli.ingest_handler_common import _parse_required_stack_tier, _write_manifest


def register_ingest_parser(
    p_ingest_sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_anthropic = p_ingest_sub.add_parser(
        "anthropic",
        help="Anthropic Messages / Computer Use offline trace adapter.",
    )
    _add_required_from_file_argument(
        p_anthropic,
        "Read Anthropic request/response rounds from a local JSON or JSONL export.",
    )
    _add_scenario_id_argument(p_anthropic, "anthropic_ingest")
    _add_architecture_argument(
        p_anthropic,
        default="single_agent",
        help_text="Architecture label for the manifest (default: single_agent).",
    )
    _add_stack_tier_argument(
        p_anthropic,
        default="within_stack",
        help_text="Default stack tier for fragments (default: within_stack).",
    )
    p_anthropic.add_argument(
        "--cross-stack-tools",
        type=str,
        default=None,
        help="Regex matched against custom tool names that should be treated as cross-stack.",
    )
    _add_state_mutation_tools_argument(
        p_anthropic,
        "Regex matched against custom tool names to emit state_mutation fragments.",
    )
    _add_actor_override_argument(p_anthropic, "Force a single actor_id for the whole trace.")
    p_anthropic.add_argument(
        "--store-thinking",
        action="store_true",
        help="Keep captured thinking-block content instead of hashing it.",
    )
    p_anthropic.add_argument(
        "--bash-readonly-pattern",
        type=str,
        default=r"^(ls|cat|head|tail|pwd|echo|grep|find|stat|whoami|id|date|env|hostname)\b",
        help="Regex for bash commands that should be treated as read-only.",
    )
    _add_out_argument(p_anthropic)
    p_anthropic.set_defaults(func=_cmd_ingest_anthropic)


def _cmd_ingest_anthropic(args: argparse.Namespace) -> int:
    """Ingest Anthropic Messages / Computer Use offline traces and write a manifest."""
    from . import AnthropicIngestOptions, load_rounds_file, rounds_to_manifest

    try:
        tier = _parse_required_stack_tier(args.stack_tier)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    opts = AnthropicIngestOptions(
        architecture=args.architecture,
        stack_tier=tier,
        cross_stack_tools_pattern=args.cross_stack_tools,
        state_mutation_tool_pattern=args.state_mutation_tools,
        actor_override=args.actor_override,
        store_thinking=args.store_thinking,
        bash_readonly_pattern=args.bash_readonly_pattern,
    )

    try:
        rounds = load_rounds_file(args.from_file)
        if not rounds:
            raise ValueError("Anthropic rounds file is empty")
        manifest = rounds_to_manifest(rounds, scenario_id=args.scenario_id, opts=opts)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _write_manifest(manifest, args.out)
    return 0


__all__ = ["register_ingest_parser"]
