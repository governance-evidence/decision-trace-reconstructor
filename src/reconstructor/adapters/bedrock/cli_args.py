"""Bedrock-specific argparse helpers for ingest command registration."""

from __future__ import annotations

import argparse


def _add_bedrock_cloudwatch_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--aws-profile",
        type=str,
        default=None,
        help="AWS profile name for live CloudWatch ingest.",
    )
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="AWS region for live CloudWatch ingest.",
    )
    parser.add_argument(
        "--start-time-ms",
        type=int,
        default=None,
        help="Lower bound for CloudWatch fetch window in epoch milliseconds.",
    )
    parser.add_argument(
        "--end-time-ms",
        type=int,
        default=None,
        help="Upper bound for CloudWatch fetch window in epoch milliseconds.",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Filter live CloudWatch sessions client-side to one Bedrock session id.",
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default=None,
        help="Filter live CloudWatch sessions client-side to one Bedrock agent id.",
    )
    parser.add_argument(
        "--memory-id",
        type=str,
        default=None,
        help="Attach Bedrock memory summaries from GetAgentMemory to live sessions.",
    )
    parser.add_argument(
        "--accept-partial-sessions",
        action="store_true",
        help="Allow Bedrock sessions with no terminal trace signal (default: reject likely truncated exports).",
    )
