"""CLI handler for OTLP ingest."""

from __future__ import annotations

import argparse
import json
import sys

from ...cli.ingest_handler_common import (
    _comma_tuple,
    _parse_required_stack_tier,
    _write_manifest,
)


def _cmd_ingest_otlp(args: argparse.Namespace) -> int:
    """Ingest OTLP JSON / JSONL / protobuf / HTTP-exported spans and write a manifest."""
    from . import (
        OtlpIngestOptions,
        load_spans_file,
        load_spans_protobuf,
        load_spans_url,
        spans_to_manifest,
    )

    try:
        tier = _parse_required_stack_tier(args.stack_tier)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    opts = OtlpIngestOptions(
        architecture=args.architecture,
        stack_tier=tier,
        within_stack_services=_comma_tuple(args.within_stack_services),
        state_mutation_tool_pattern=args.state_mutation_tools,
        actor_override=args.actor_override,
        accept_sampled=args.accept_sampled,
        sampling_rate=args.sampling_rate,
        store_content=args.store_content,
        auto_architecture=args.auto_architecture,
        schema_version_tolerance=args.schema_version_tolerance,
    )

    try:
        if _otlp_input_count(args) != 1:
            raise ValueError(
                "exactly one of --from-file / --from-otlp-collector / --from-otel-protobuf is required"
            )
        if args.from_file is not None:
            spans = load_spans_file(args.from_file)
        elif args.from_otel_protobuf is not None:
            spans = load_spans_protobuf(args.from_otel_protobuf)
        else:
            spans = load_spans_url(args.from_otlp_collector, timeout=args.collector_timeout)
        manifest = spans_to_manifest(spans, scenario_id=args.scenario_id, opts=opts)
    except (ImportError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _write_manifest(manifest, args.out)
    return 0


def _otlp_input_count(args: argparse.Namespace) -> int:
    return sum(
        1
        for value in (args.from_file, args.from_otlp_collector, args.from_otel_protobuf)
        if value is not None
    )
