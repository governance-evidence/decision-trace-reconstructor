"""CLI registration for reproducible evaluation commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..evaluation.defaults import DEFAULT_EVALUATION_OUT_DIR, DEFAULT_SYNTHETIC_SEEDS_PER_CELL


def _cmd_evaluate_synthetic(args: argparse.Namespace) -> int:
    from ..evaluation import run_synthetic as mod

    return int(
        mod.main(
            [
                "--out",
                str(args.out),
                "--seeds-per-cell",
                str(args.seeds_per_cell),
            ]
        )
        or 0
    )


def _cmd_evaluate_named(args: argparse.Namespace) -> int:
    from ..evaluation import run_named as mod

    return int(
        mod.main(
            [
                "--out",
                str(args.out),
            ]
        )
        or 0
    )


def register_evaluation_command(
    sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p_evaluate = sub.add_parser(
        "evaluate",
        help="Run reproducible evaluation scenarios and emit result artifacts.",
    )
    p_evaluate_sub = p_evaluate.add_subparsers(dest="evaluation_target", required=True)

    p_synth = p_evaluate_sub.add_parser(
        "synthetic",
        help="Evaluate the 3x2 + baseline synthetic matrix (140 scenarios).",
    )
    p_synth.add_argument("--out", type=Path, default=DEFAULT_EVALUATION_OUT_DIR)
    p_synth.add_argument(
        "--seeds-per-cell",
        type=int,
        default=DEFAULT_SYNTHETIC_SEEDS_PER_CELL,
    )
    p_synth.set_defaults(func=_cmd_evaluate_synthetic)

    p_named = p_evaluate_sub.add_parser(
        "named",
        help="Evaluate the named-incident scenarios.",
    )
    p_named.add_argument("--out", type=Path, default=DEFAULT_EVALUATION_OUT_DIR)
    p_named.set_defaults(func=_cmd_evaluate_named)
