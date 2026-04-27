"""Run the full synthetic evaluation: 120 agentic + 20 baseline scenarios.

Outputs (raw JSON is canonical wire format; siblings are governance-grade):
- ``cells.json``           -- per-cell aggregates (Pydantic-validated)
- ``cells.jsonld``         -- PROV-O summary graph
- ``per_property.json``    -- per-decision-event-property feasibility distributions
- ``per_scenario.json``    -- per-scenario summary (140 rows)
- ``per_scenario.jsonld``  -- PROV-O summary graph (one DecisionChain per row)
- ``per_scenario.parquet`` -- Apache Parquet sibling (only if pyarrow installed)
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from ..synthetic.generator import generate_matrix
from .defaults import DEFAULT_EVALUATION_OUT_DIR, DEFAULT_SYNTHETIC_SEEDS_PER_CELL
from .synthetic_console import _print_tables
from .synthetic_evaluation import _evaluate_scenarios
from .synthetic_outputs import _build_outputs, _write_outputs


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds-per-cell", type=int, default=DEFAULT_SYNTHETIC_SEEDS_PER_CELL)
    parser.add_argument("--out", type=Path, default=DEFAULT_EVALUATION_OUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    scenarios = generate_matrix(seeds_per_cell=args.seeds_per_cell)
    print(f"Generated {len(scenarios)} scenarios")

    evaluation = _evaluate_scenarios(scenarios)
    outputs = _build_outputs(evaluation)
    _write_outputs(args.out, outputs)
    _print_tables(outputs.cells, outputs.per_property_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
