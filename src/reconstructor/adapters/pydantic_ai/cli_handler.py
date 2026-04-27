"""CLI handler for Pydantic AI ingest."""

from __future__ import annotations

import argparse
import json
import sys

from ...cli.ingest_handler_common import _parse_required_stack_tier, _write_manifest


def _cmd_ingest_pydantic_ai(args: argparse.Namespace) -> int:
    """Ingest Pydantic AI offline run records and write a fragments manifest."""
    from . import PydanticAIIngestOptions, load_runs_file, runs_to_manifest

    try:
        tier = _parse_required_stack_tier(args.stack_tier)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    opts = PydanticAIIngestOptions(
        architecture=args.architecture,
        auto_architecture=args.auto_architecture,
        stack_tier=tier,
        cross_stack_tools_pattern=args.cross_stack_tools,
        state_mutation_tool_pattern=args.state_mutation_tools,
        takeover_tool_pattern=args.takeover_tool_pattern,
        human_approval_pattern=args.human_approval_pattern,
        emit_system_prompt=args.emit_system_prompt,
        actor_override=args.actor_override,
    )

    try:
        runs = load_runs_file(args.from_file)
        if not runs:
            raise ValueError("Pydantic AI input is empty")
        manifest = runs_to_manifest(runs, scenario_id=args.scenario_id, opts=opts)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _write_manifest(manifest, args.out)
    return 0
