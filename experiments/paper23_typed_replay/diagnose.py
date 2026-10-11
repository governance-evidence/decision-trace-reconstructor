"""Append a reproducible gap census without changing replay predictions."""

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

from experiments.paper23.storage import read, write
from experiments.paper23_typed_replay.run import sha


def diagnose(root):
    target = root / "diagnostic.json"
    if target.exists():
        raise ValueError("Preserve existing diagnostic")
    rows = read(root / "rows.json")
    gaps = read(root / "typed-gaps.json")
    census = defaultdict(set)
    for row in gaps:
        for gap in row["gap"].split("; "):
            reason = re.sub(r"^[^:]+: ", "", gap)
            census[(row["property"], reason)].add(row["packet_id"])
    output = dict(
        script_sha256=sha(Path(__file__)),
        input_sha256={p: sha(root / p) for p in ("rows.json", "typed-gaps.json", "summary.json")},
        unit="Packets per property and reason; reasons overlap and must not be summed as rows",
        gap_census=[
            dict(property=p, reason=r, packets=len(ids), packet_ids=sorted(ids))
            for (p, r), ids in sorted(census.items())
        ],
        typed_nonfull_on_reference_full=dict(
            Counter(
                r["property"]
                for r in rows
                if r["reference"] == "fully_supported" and r["typed"] != "fully_fillable"
            )
        ),
        coverage_baseline_binary_disagreements=sum(
            (r["coverage"] == "fully_fillable") != (r["baseline"] == "fully_fillable") for r in rows
        ),
        residual_typed_false_full=[
            r
            for r in rows
            if r["typed"] == "fully_fillable" and r["reference"] != "fully_supported"
        ],
    )
    write(target, output)
    print(output["typed_nonfull_on_reference_full"])
    print([(v["property"], v["reason"], v["packets"]) for v in output["gap_census"]])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    diagnose(parser.parse_args().root)
