"""CLI handler for Agent Framework ingest."""

from __future__ import annotations

import argparse
import json
import sys

from ...cli.ingest_handler_common import _parse_required_stack_tier, _write_manifest


def _cmd_ingest_agentframework(args: argparse.Namespace) -> int:
    """Ingest Agent Framework events and write a fragments manifest."""
    from . import (
        AgentFrameworkIngestOptions,
        events_to_manifest,
        load_events_file,
    )

    try:
        tier = _parse_required_stack_tier(args.stack_tier)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    opts = AgentFrameworkIngestOptions(
        architecture=args.architecture,
        auto_architecture=args.auto_architecture,
        stack_tier=tier,
        cross_stack_tools_pattern=args.cross_stack_tools,
        state_mutation_tool_pattern=args.state_mutation_tools,
        actor_override=args.actor_override,
        runtime=args.runtime,
        topic_filter=args.topic_filter,
    )

    try:
        events = load_events_file(args.from_file)
        if not events:
            raise ValueError("Agent Framework input is empty")
        manifest = events_to_manifest(events, scenario_id=args.scenario_id, opts=opts)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _write_manifest(manifest, args.out)
    return 0
