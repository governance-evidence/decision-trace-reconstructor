"""Shared argparse helpers for ingest command registration."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..core.architecture import AGENTIC_ARCHITECTURES

_ARCHITECTURE_CHOICES = tuple(arch.value for arch in AGENTIC_ARCHITECTURES)
_STACK_TIER_CHOICES = ("within_stack", "cross_stack")
_OUT_MANIFEST_HELP = "Output fragments-manifest path. Use '-' to write to stdout."


def _add_required_from_file_argument(
    parser: argparse.ArgumentParser,
    help_text: str,
) -> None:
    parser.add_argument(
        "--from-file",
        type=Path,
        required=True,
        help=help_text,
    )


def _add_scenario_id_argument(
    parser: argparse.ArgumentParser,
    default: str,
    help_text: str | None = None,
) -> None:
    parser.add_argument(
        "--scenario-id",
        type=str,
        default=default,
        help=help_text or f"Scenario id to embed in the manifest (default: {default}).",
    )


def _add_architecture_argument(
    parser: argparse.ArgumentParser,
    default: str | None,
    help_text: str,
) -> None:
    parser.add_argument(
        "--architecture",
        type=str,
        default=default,
        choices=_ARCHITECTURE_CHOICES,
        help=help_text,
    )


def _add_auto_architecture_argument(
    parser: argparse.ArgumentParser,
    help_text: str,
) -> None:
    parser.add_argument(
        "--auto-architecture",
        action="store_true",
        help=help_text,
    )


def _add_stack_tier_argument(
    parser: argparse.ArgumentParser,
    default: str | None,
    help_text: str,
    choices: tuple[str, ...] = _STACK_TIER_CHOICES,
) -> None:
    parser.add_argument(
        "--stack-tier",
        type=str,
        default=default,
        choices=choices,
        help=help_text,
    )


def _add_state_mutation_tools_argument(
    parser: argparse.ArgumentParser,
    help_text: str,
) -> None:
    parser.add_argument(
        "--state-mutation-tools",
        type=str,
        default=None,
        help=help_text,
    )


def _add_actor_override_argument(
    parser: argparse.ArgumentParser,
    help_text: str,
) -> None:
    parser.add_argument(
        "--actor-override",
        type=str,
        default=None,
        help=help_text,
    )


def _add_out_argument(
    parser: argparse.ArgumentParser,
    help_text: str = _OUT_MANIFEST_HELP,
) -> None:
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("fragments.json"),
        help=help_text,
    )
