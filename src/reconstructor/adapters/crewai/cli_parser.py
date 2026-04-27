"""Argparse builder for the CrewAI ingest adapter."""

from __future__ import annotations

import argparse

from ...cli.ingest_common import (
    _add_actor_override_argument,
    _add_architecture_argument,
    _add_auto_architecture_argument,
    _add_out_argument,
    _add_required_from_file_argument,
    _add_scenario_id_argument,
    _add_stack_tier_argument,
    _add_state_mutation_tools_argument,
)
from .cli_handler import _cmd_ingest_crewai


def register_ingest_parser(
    p_ingest_sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_crewai = p_ingest_sub.add_parser(
        "crewai",
        help="CrewAI telemetry offline adapter.",
    )
    _add_required_from_file_argument(
        p_crewai,
        "Read CrewAI TelemetryEvent records from a local JSON or JSONL export.",
    )
    _add_scenario_id_argument(p_crewai, "crewai_ingest")
    _add_architecture_argument(
        p_crewai,
        default="multi_agent",
        help_text="Architecture label for the manifest when auto-detection is disabled.",
    )
    _add_auto_architecture_argument(
        p_crewai,
        "Infer architecture from agent count, process type, and human_input flags.",
    )
    _add_stack_tier_argument(
        p_crewai,
        default="within_stack",
        help_text="Default stack tier for CrewAI fragments (default: within_stack).",
    )
    p_crewai.add_argument(
        "--cross-stack-tools",
        type=str,
        default=None,
        help="Regex matched against tool names that should be treated as cross-stack.",
    )
    _add_state_mutation_tools_argument(
        p_crewai,
        "Regex matched against tool names to emit paired state_mutation fragments.",
    )
    _add_actor_override_argument(p_crewai, "Force a single actor_id for the whole Crew trace.")
    p_crewai.add_argument(
        "--crew-name",
        type=str,
        default=None,
        help="Filter a multi-crew transcript down to one crew_name.",
    )
    p_crewai.add_argument(
        "--emit-config-snapshot",
        dest="emit_config_snapshot",
        action="store_true",
        default=True,
        help="Emit crew_kickoff_started as config_snapshot (default: on).",
    )
    p_crewai.add_argument(
        "--no-emit-config-snapshot",
        dest="emit_config_snapshot",
        action="store_false",
        help="Do not emit crew_kickoff_started as config_snapshot.",
    )
    _add_out_argument(p_crewai)
    p_crewai.set_defaults(func=_cmd_ingest_crewai)
