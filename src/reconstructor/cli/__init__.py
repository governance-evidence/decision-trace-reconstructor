"""Command-line interface for the Decision Trace Reconstructor.

Entry point declared in ``pyproject.toml`` as ``decision-trace = reconstructor.cli:main``.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from .evaluation import register_evaluation_command
from .ingest import register_ingest_command, register_validate_and_schema_commands
from .reconstruct import add_reconstruct_parser

if TYPE_CHECKING:
    from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decision-trace",
        description="Decision Trace Reconstructor",
    )
    parser.add_argument("--version", action="version", version=_resolve_version())
    sub = parser.add_subparsers(dest="command", required=True)

    add_reconstruct_parser(sub)
    register_evaluation_command(sub)
    register_validate_and_schema_commands(sub)
    register_ingest_command(sub)

    return parser


def _resolve_version() -> str:
    from .. import __version__

    return f"decision-trace {__version__}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
