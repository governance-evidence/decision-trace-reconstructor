"""OTLP-specific argparse helpers for ingest command registration."""

from __future__ import annotations

import argparse


def _add_otlp_within_stack_services_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--within-stack-services",
        type=str,
        default="",
        help="Comma-separated service names / hosts considered within-stack.",
    )


def _add_otlp_sampling_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--accept-sampled",
        action="store_true",
        help="Allow traces whose declared sampling rate is below 0.5.",
    )
    parser.add_argument(
        "--sampling-rate",
        type=float,
        default=None,
        help="Explicit trace sampling rate override.",
    )
    parser.add_argument(
        "--store-content",
        action="store_true",
        help="Keep raw message / tool content instead of hashed summaries.",
    )
    parser.add_argument(
        "--schema-version-tolerance",
        type=str,
        default="lenient",
        choices=("strict", "lenient"),
        help="Whether to accept legacy llm.* attributes (default: lenient).",
    )
    parser.add_argument(
        "--collector-timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds for --from-otlp-collector (default: 30).",
    )
