"""Argparse registration for validation, schema, and ingest commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from .adapter_registry import iter_adapter_ingest_registrars
from .ingest_schema_handlers import _cmd_export_schemas, _cmd_validate_generic_jsonl


def register_validate_and_schema_commands(
    sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_validate = sub.add_parser(
        "validate",
        help="Validate adapter-specific mapping/config surfaces without writing fragments.",
    )
    p_validate_sub = p_validate.add_subparsers(dest="validate_target", required=True)

    p_validate_generic = p_validate_sub.add_parser(
        "generic-jsonl",
        help="Validate a Generic JSONL mapping file against a sample log export.",
    )
    p_validate_generic.add_argument(
        "--mapping",
        type=Path,
        required=True,
        help="Path to the Generic JSONL mapping config (YAML or JSON).",
    )
    p_validate_generic.add_argument(
        "--sample-from",
        type=Path,
        required=True,
        help="Path to a JSONL sample file used for validation.",
    )
    p_validate_generic.set_defaults(func=_cmd_validate_generic_jsonl)

    p_schemas = sub.add_parser(
        "export-schemas",
        help="Regenerate JSON Schema files from Pydantic models.",
    )
    p_schemas.add_argument("--out", type=Path, default=Path("docs/schemas"))
    p_schemas.set_defaults(func=_cmd_export_schemas)


def register_ingest_command(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_ingest = sub.add_parser(
        "ingest",
        help="Translate vendor traces into a fragments manifest.",
    )
    p_ingest_sub = p_ingest.add_subparsers(dest="adapter", required=True)

    for _adapter_name, register_ingest_parser in iter_adapter_ingest_registrars():
        register_ingest_parser(p_ingest_sub)
