"""Compatibility facade for shared ingest argparse helpers."""

from __future__ import annotations

from .ingest_common_args import (
    _add_actor_override_argument,
    _add_architecture_argument,
    _add_auto_architecture_argument,
    _add_out_argument,
    _add_required_from_file_argument,
    _add_scenario_id_argument,
    _add_stack_tier_argument,
    _add_state_mutation_tools_argument,
)

__all__ = [
    "_add_actor_override_argument",
    "_add_architecture_argument",
    "_add_auto_architecture_argument",
    "_add_out_argument",
    "_add_required_from_file_argument",
    "_add_scenario_id_argument",
    "_add_stack_tier_argument",
    "_add_state_mutation_tools_argument",
]
