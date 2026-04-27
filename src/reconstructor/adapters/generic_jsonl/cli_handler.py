"""CLI handler for Generic JSONL ingest."""

from __future__ import annotations

import argparse
import json
import sys

from ...cli.ingest_handler_common import (
    _comma_tuple,
    _parse_optional_stack_tier,
    _write_manifest,
)


def _cmd_ingest_generic_jsonl(args: argparse.Namespace) -> int:
    """Ingest Generic JSONL logs and write a fragments manifest."""
    from . import (
        GenericJsonlIngestOptions,
        iter_jsonl_stream,
        iter_records_file,
        load_mapping_file,
        records_to_manifest,
        validate_mapping_sample,
    )

    try:
        tier = _parse_optional_stack_tier(args.stack_tier)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    opts = GenericJsonlIngestOptions(
        architecture=args.architecture,
        stack_tier=tier,
        strict_unknown_kinds=args.strict_unknown_kinds,
        redact_fields=_comma_tuple(args.redact_fields),
        actor_override=args.actor_override,
    )

    try:
        mapping = load_mapping_file(args.mapping)
        records = (
            iter_jsonl_stream(sys.stdin) if args.from_stdin else iter_records_file(args.from_file)
        )
        if not records:
            raise ValueError("Generic JSONL input is empty")
        issues = validate_mapping_sample(mapping, records[:100])
        if issues:
            raise ValueError(issues[0])
        manifest = records_to_manifest(records, mapping, scenario_id=args.scenario_id, opts=opts)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _write_manifest(manifest, args.out)
    return 0
