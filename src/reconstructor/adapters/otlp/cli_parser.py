"""Argparse builder for the OTLP ingest adapter."""

from __future__ import annotations

import argparse
from pathlib import Path

from ...cli.ingest_common import (
    _add_actor_override_argument,
    _add_architecture_argument,
    _add_auto_architecture_argument,
    _add_out_argument,
    _add_scenario_id_argument,
    _add_stack_tier_argument,
    _add_state_mutation_tools_argument,
)
from .cli_args import _add_otlp_sampling_options, _add_otlp_within_stack_services_argument
from .cli_handler import _cmd_ingest_otlp


def register_ingest_parser(
    p_ingest_sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_otlp = p_ingest_sub.add_parser(
        "otlp",
        help="OpenTelemetry GenAI OTLP adapter (JSON, JSONL, protobuf, or HTTP export ingest).",
    )
    p_otlp_src = p_otlp.add_mutually_exclusive_group(required=True)
    p_otlp_src.add_argument(
        "--from-file",
        type=Path,
        help="Read OTLP spans from a local JSON or JSONL file.",
    )
    p_otlp_src.add_argument(
        "--from-otlp-collector",
        type=str,
        help="Fetch OTLP spans from an HTTP(S) endpoint returning OTLP JSON, JSONL, or protobuf.",
    )
    p_otlp_src.add_argument(
        "--from-otel-protobuf",
        type=Path,
        help="Read an ExportTraceServiceRequest protobuf file.",
    )
    _add_scenario_id_argument(p_otlp, "otlp_ingest")
    _add_architecture_argument(
        p_otlp,
        default="single_agent",
        help_text="Architecture label for the manifest (default: single_agent).",
    )
    _add_auto_architecture_argument(
        p_otlp,
        "Infer architecture from agent ids / invoke_agent spans.",
    )
    _add_stack_tier_argument(
        p_otlp,
        default="within_stack",
        help_text="Default stack tier for fragments (default: within_stack).",
    )
    _add_otlp_within_stack_services_argument(p_otlp)
    _add_state_mutation_tools_argument(
        p_otlp,
        "Regex matched against tool names to emit paired state_mutation fragments.",
    )
    _add_actor_override_argument(p_otlp, "Force a single actor_id for the whole trace.")
    _add_otlp_sampling_options(p_otlp)
    _add_out_argument(p_otlp)
    p_otlp.set_defaults(func=_cmd_ingest_otlp)
