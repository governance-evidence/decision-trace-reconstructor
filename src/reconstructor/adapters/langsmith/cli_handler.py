"""CLI handler for LangSmith ingest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ...cli.ingest_handler_common import _parse_required_stack_tier, _write_manifest


def _cmd_ingest_langsmith(args: argparse.Namespace) -> int:
    """Ingest a LangSmith trace and write a fragments manifest."""
    from . import (
        LangSmithIngestOptions,
        runs_to_manifest,
    )

    if _langsmith_input_count(args) != 1:
        print(
            "error: exactly one of --from-file / --trace-id / --run-id is required",
            file=sys.stderr,
        )
        return 2

    try:
        tier = _parse_required_stack_tier(args.stack_tier)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    opts = LangSmithIngestOptions(
        architecture=args.architecture,
        stack_tier=tier,
        state_mutation_tool_pattern=args.state_mutation_tools,
        actor_override=args.actor_override,
    )

    runs = _load_langsmith_runs(args)
    if runs is None:
        return 2

    manifest = runs_to_manifest(runs, scenario_id=args.scenario_id, opts=opts)

    _write_manifest(manifest, args.out)
    return 0


def _langsmith_input_count(args: argparse.Namespace) -> int:
    return sum(1 for f in (args.from_file, args.trace_id, args.run_id) if f is not None)


def _load_langsmith_runs(args: argparse.Namespace) -> list[Any] | None:
    if args.from_file:
        data = json.loads(Path(args.from_file).read_text())
        runs = data["runs"] if isinstance(data, dict) and "runs" in data else data
        if isinstance(runs, list):
            return runs
        print(
            'error: --from-file must contain a JSON array of run dicts (or {"runs": [...]})',
            file=sys.stderr,
        )
        return None
    return _fetch_langsmith_runs(args)


def _fetch_langsmith_runs(args: argparse.Namespace) -> list[Any] | None:
    try:
        from langsmith import Client

        from . import fetch_run_subtree, fetch_trace
    except ImportError:
        print(
            "error: network ingest requires the [langsmith] extra. "
            "Install with `pip install -e '.[langsmith]'`.",
            file=sys.stderr,
        )
        return None
    client = Client(api_key=args.api_key, api_url=args.api_url)
    if args.trace_id:
        return fetch_trace(client, args.trace_id, project_name=args.project)
    return fetch_run_subtree(client, args.run_id)
