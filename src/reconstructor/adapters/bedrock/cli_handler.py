"""CLI handler for Bedrock ingest."""

from __future__ import annotations

import argparse
import json
import sys

from ...cli.ingest_handler_common import (
    _comma_tuple,
    _parse_required_stack_tier,
    _write_manifest,
)


def _cmd_ingest_bedrock(args: argparse.Namespace) -> int:
    """Ingest Bedrock AgentCore traces and write a fragments manifest."""
    from . import (
        BedrockIngestOptions,
        load_sessions_cloudwatch,
        load_sessions_file,
        sessions_to_manifest,
        validate_sessions_complete,
    )

    try:
        tier = _parse_required_stack_tier(args.stack_tier)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    opts = BedrockIngestOptions(
        architecture=args.architecture,
        stack_tier=tier,
        cross_stack_action_groups=_comma_tuple(args.cross_stack_action_groups),
        state_mutation_tool_pattern=args.state_mutation_tools,
        actor_override=args.actor_override,
        auto_architecture=args.auto_architecture,
        store_content=args.store_content,
    )

    try:
        if args.from_file is not None:
            sessions = load_sessions_file(args.from_file)
        else:
            sessions = load_sessions_cloudwatch(
                args.log_group,
                aws_profile=args.aws_profile,
                region=args.region,
                start_time_ms=args.start_time_ms,
                end_time_ms=args.end_time_ms,
                session_id=args.session_id,
                agent_id=args.agent_id,
                memory_id=args.memory_id,
            )
        if not args.accept_partial_sessions:
            validate_sessions_complete(sessions)
        manifest = sessions_to_manifest(sessions, scenario_id=args.scenario_id, opts=opts)
    except (ImportError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _write_manifest(manifest, args.out)
    return 0
