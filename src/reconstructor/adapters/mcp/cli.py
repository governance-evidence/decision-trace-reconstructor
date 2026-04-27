"""CLI integration for the MCP adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ...cli.ingest_common import (
    _add_actor_override_argument,
    _add_architecture_argument,
    _add_out_argument,
    _add_scenario_id_argument,
    _add_state_mutation_tools_argument,
)
from ...cli.ingest_handler_common import _write_manifest


def register_ingest_parser(
    p_ingest_sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_mcp = p_ingest_sub.add_parser(
        "mcp",
        help="Model Context Protocol transcript adapter.",
    )
    p_mcp_src = p_mcp.add_mutually_exclusive_group(required=True)
    p_mcp_src.add_argument(
        "--from-file",
        type=Path,
        help="Read MCP transcript entries from a local JSON or JSONL export.",
    )
    p_mcp_src.add_argument(
        "--from-claude-desktop",
        action="store_true",
        help="Auto-locate Claude Desktop MCP logs on the local machine.",
    )
    _add_scenario_id_argument(p_mcp, "mcp_ingest")
    _add_architecture_argument(
        p_mcp,
        default="single_agent",
        help_text="Architecture label for the manifest; MCP itself carries no architecture signal.",
    )
    _add_state_mutation_tools_argument(
        p_mcp,
        "Regex matched against MCP tool names to emit paired state_mutation fragments.",
    )
    p_mcp.add_argument(
        "--emit-tools-list",
        action="store_true",
        help="Include tool roster responses as config_snapshot fragments.",
    )
    p_mcp.add_argument(
        "--max-state-mutations-per-resource",
        type=int,
        default=10,
        help="Maximum resource-updated notifications to emit per resource (default: 10).",
    )
    p_mcp.add_argument(
        "--store-uris",
        action="store_true",
        help="Keep resource URIs raw instead of hashing them.",
    )
    _add_actor_override_argument(
        p_mcp,
        "Override the client-side actor id for MCP client requests.",
    )
    p_mcp.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Filter a multi-session transcript down to one session id.",
    )
    _add_out_argument(p_mcp)
    p_mcp.set_defaults(func=_cmd_ingest_mcp)


def _cmd_ingest_mcp(args: argparse.Namespace) -> int:
    """Ingest MCP transcript logs and write a fragments manifest."""
    from . import (
        McpIngestOptions,
        find_claude_desktop_logs,
        load_transcript_file,
        transcript_to_manifest,
    )

    opts = McpIngestOptions(
        architecture=args.architecture,
        state_mutation_tool_pattern=args.state_mutation_tools,
        emit_tools_list=args.emit_tools_list,
        max_state_mutations_per_resource=args.max_state_mutations_per_resource,
        store_uris=args.store_uris,
        actor_override=args.actor_override,
        session_id=args.session_id,
    )

    try:
        if args.from_file is not None:
            frames = load_transcript_file(args.from_file)
        else:
            log_paths = find_claude_desktop_logs()
            if not log_paths:
                raise ValueError("could not locate Claude Desktop MCP logs")
            frames = []
            for path in log_paths:
                frames.extend(load_transcript_file(path))
        if not frames:
            raise ValueError("MCP transcript input is empty")
        manifest = transcript_to_manifest(frames, scenario_id=args.scenario_id, opts=opts)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _write_manifest(manifest, args.out)
    return 0


__all__ = ["register_ingest_parser"]
