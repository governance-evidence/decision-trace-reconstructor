"""CLI handler for OpenAI Agents ingest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ...cli.ingest_handler_common import (
    _comma_tuple,
    _parse_required_stack_tier,
    _write_manifest,
)


def _cmd_ingest_openai_agents(args: argparse.Namespace) -> int:
    """Ingest OpenAI Agents SDK offline traces and write fragment manifests."""
    from . import (
        OpenAIAgentsIngestOptions,
        load_traces_file,
        trace_to_manifest,
        traces_to_manifests,
    )

    try:
        tier = _parse_required_stack_tier(args.stack_tier)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    opts = OpenAIAgentsIngestOptions(
        architecture=args.architecture,
        stack_tier=tier,
        cross_stack_tools=_comma_tuple(args.cross_stack_tools),
        state_mutation_tool_pattern=args.state_mutation_tools,
        actor_override=args.actor_override,
        store_reasoning=args.store_reasoning,
        auto_architecture=args.auto_architecture,
    )

    try:
        traces = load_traces_file(args.from_file)
        if not traces:
            raise ValueError("OpenAI Agents trace file is empty")
        if args.group_into_scenarios or len(traces) > 1:
            manifests = traces_to_manifests(
                traces,
                scenario_id_prefix=args.scenario_id,
                opts=opts,
                group_into_scenarios=args.group_into_scenarios,
            )
        else:
            manifests = [trace_to_manifest(traces[0], scenario_id=args.scenario_id, opts=opts)]
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return _write_openai_agents_manifests(manifests, args)


def _write_openai_agents_manifests(
    manifests: list[dict[str, Any]],
    args: argparse.Namespace,
) -> int:
    if len(manifests) == 1:
        return _write_single_openai_agents_manifest(manifests[0], args)
    if args.out == Path("-"):
        print(
            "error: cannot write multiple OpenAI manifests to stdout; use a directory path",
            file=sys.stderr,
        )
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    for manifest in manifests:
        path = args.out / f"{manifest['scenario_id']}.json"
        _write_manifest(manifest, path)
    return 0


def _write_single_openai_agents_manifest(
    manifest: dict[str, Any],
    args: argparse.Namespace,
) -> int:
    if args.out == Path("-"):
        _write_manifest(manifest, args.out)
    elif args.group_into_scenarios and args.out.suffix == "":
        args.out.mkdir(parents=True, exist_ok=True)
        path = args.out / f"{manifest['scenario_id']}.json"
        _write_manifest(manifest, path)
    else:
        _write_manifest(manifest, args.out)
    return 0
