"""Validation and schema-export CLI handlers."""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_validate_generic_jsonl(args: argparse.Namespace) -> int:
    """Validate a Generic JSONL mapping against a sample file."""
    from ..adapters.generic_jsonl import validate_mapping_file

    try:
        issues = validate_mapping_file(args.mapping, args.sample_from)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if issues:
        for issue in issues:
            print(f"error: {issue}", file=sys.stderr)
        return 2

    print(f"validated {args.mapping} against {args.sample_from}")
    return 0


def _cmd_export_schemas(args: argparse.Namespace) -> int:
    from ..output.models import (
        CellResults,
        GenericJsonlMappingConfig,
        NamedIncidentResults,
        PerPropertyTable,
        PerScenarioResults,
    )

    targets = (
        ("cells.schema.json", CellResults),
        ("generic_jsonl_mapping.schema.json", GenericJsonlMappingConfig),
        ("per_property.schema.json", PerPropertyTable),
        ("per_scenario.schema.json", PerScenarioResults),
        ("named_incidents.schema.json", NamedIncidentResults),
    )
    args.out.mkdir(parents=True, exist_ok=True)
    for filename, model_cls in targets:
        schema = model_cls.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"https://decisiontrace.org/reconstructor/v0.1.0/schemas/{filename}"
        path = args.out / filename
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
        print(f"wrote {path}")
    return 0
