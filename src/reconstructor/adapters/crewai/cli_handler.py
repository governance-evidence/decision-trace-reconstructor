"""CLI handler for CrewAI ingest."""

from __future__ import annotations

import argparse
import json
import sys

from ...cli.ingest_handler_common import _parse_required_stack_tier, _write_manifest


def _cmd_ingest_crewai(args: argparse.Namespace) -> int:
    """Ingest CrewAI telemetry events and write a fragments manifest."""
    from . import CrewAIIngestOptions, events_to_manifest, load_events_file

    try:
        tier = _parse_required_stack_tier(args.stack_tier)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    opts = CrewAIIngestOptions(
        architecture=args.architecture,
        auto_architecture=args.auto_architecture,
        stack_tier=tier,
        cross_stack_tools_pattern=args.cross_stack_tools,
        state_mutation_tool_pattern=args.state_mutation_tools,
        actor_override=args.actor_override,
        crew_name=args.crew_name,
        emit_config_snapshot=args.emit_config_snapshot,
    )

    try:
        events = load_events_file(args.from_file)
        if not events:
            raise ValueError("CrewAI telemetry input is empty")
        manifest = events_to_manifest(events, scenario_id=args.scenario_id, opts=opts)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _write_manifest(manifest, args.out)
    return 0
