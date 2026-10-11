"""Offline, non-overwriting replay against unchanged V5 AI assessments."""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from experiments.paper23.packets import ROWS, baseline, crosswalk
from experiments.paper23.packets import adapt as legacy_adapt
from experiments.paper23.storage import digest, read, write
from experiments.paper23_analysis.scoring import metrics, paired
from experiments.paper23_typed_replay.adapter import VERSION, adapt

REPO = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob("*")) if p.is_file()}


def run(source, output):
    source, output = source.resolve(), output.resolve()
    if output.exists():
        raise ValueError("Preserve earlier outputs; choose an absent directory")
    if output == source or source in output.parents:
        raise ValueError("Output must be outside the frozen V5 directory")
    before = inventory(source)
    for name, expected in read(source / "freeze.json")["inputs"].items():
        if sha(source / name) != expected:
            raise ValueError(f"V5 frozen input differs: {name}")
    archives = {str(p): sha(p) for p in sorted(source.parent.glob("paper23-*delivery.zip"))}
    answers = {}
    for which in ("reduced", "full"):
        f = read(source / "annotations" / f"{which}.frozen.json")
        if digest(f["assessments"]) != f["source_sha256"]:
            raise ValueError("Reference freeze changed")
        for a in f["assessments"]:
            if a["packet_id"] in answers or a["status"] != "complete":
                raise ValueError("Duplicate or incomplete reference")
            answers[a["packet_id"]] = a
    index = read(source / "main-packet-index.json")
    if len(index) != 72 or len(answers) != 72 or set(answers) != {e["packet_id"] for e in index}:
        raise ValueError("Expected the exact 72-packet population")
    old_rows = read(source / "scores/rows.json")
    old = {(r["packet_id"], r["property"]): r for r in old_rows}
    if len(old) != 432:
        raise ValueError("Expected 432 old property rows")
    output.mkdir(parents=True)
    shutil.copyfile(Path(__file__).with_name("PROTOCOL.md"), output / "PROTOCOL.md")
    for area in ("src", "experiments"):
        shutil.copytree(
            REPO / area,
            output / "code" / area,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    write(
        output / "freeze.json",
        dict(
            time=time.time(),
            adapter=VERSION,
            v5_root=str(source),
            v5_files=before,
            archives=archives,
            code=inventory(output / "code"),
            protocol_sha256=sha(output / "PROTOCOL.md"),
        ),
    )
    shutil.copyfile(source / "scores/rows.json", output / "original-v5-rows.json")
    for which in ("reduced", "full"):
        shutil.copyfile(
            source / "annotations" / f"{which}.frozen.json", output / f"{which}.frozen.json"
        )
    rows, failures, gaps = [], [], []
    started = time.time()
    for entry in index:
        pid = entry["packet_id"]
        packet_path = source / "packets/main" / f"{pid}.json"
        packet = read(packet_path)
        if digest(packet) != entry["sha256"]:
            raise ValueError("Packet digest differs from frozen index")
        work = output / "packets" / pid
        work.mkdir(parents=True)
        shutil.copyfile(packet_path, work / "source-packet.json")
        typed, audit = adapt(packet)
        write(work / "adapter-audit.json", audit)
        predictions = {}
        for mode, manifest in [("coverage", legacy_adapt(packet)), ("typed", typed)]:
            destination = work / mode
            write(destination / "manifest.json", manifest)
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "reconstructor.cli",
                    "reconstruct",
                    str(destination / "manifest.json"),
                    "--out",
                    str(destination),
                ],
                cwd=output / "code",
                capture_output=True,
                text=True,
                timeout=45,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONPATH": str(output / "code/src"),
                },
            )
            write(
                destination / "process.json",
                dict(returncode=process.returncode, stdout=process.stdout, stderr=process.stderr),
            )
            if process.returncode:
                failures.append(dict(packet_id=pid, mode=mode))
                predictions[mode] = {}
            else:
                report = read(destination / "feasibility.json")
                predictions[mode] = {p["property"]: p["category"] for p in report["per_property"]}
                if mode == "typed":
                    gaps.extend(
                        dict(packet_id=pid, **p)
                        for p in report["per_property"]
                        if p["property"] in ROWS and p["category"] != "fully_fillable"
                    )
        reference = crosswalk(answers[pid]["assessment"]["questions"])
        simple = baseline(packet)
        for prop in ROWS:
            row = old[(pid, prop)].copy()
            if (
                row["reference"] != reference[prop]
                or row["baseline"] != simple[prop]
                or row["excluded"]
            ):
                raise ValueError("Reference, baseline or population changed")
            row["legacy_dtr"] = row.pop("dtr")
            row.update(
                {
                    mode: values.get(prop, "processing_failure")
                    for mode, values in predictions.items()
                }
            )
            rows.append(row)
    fields = ("legacy_dtr", "coverage", "typed", "baseline")
    summary = dict(
        packets=72,
        property_rows=len(rows),
        failures=failures,
        adapter=VERSION,
        reference="Frozen V5 typed-eligibility plus Claude Sonnet 4.6 assessment; no independent human truth",
        metrics={f: metrics(rows, f) for f in fields},
        paired={f: paired(rows, f) for f in fields},
        by_property={
            p: {f: metrics([r for r in rows if r["property"] == p], f) for f in fields}
            for p in ROWS
        },
        changed_rows={f: sum(r[f] != r["legacy_dtr"] for r in rows) for f in ("coverage", "typed")},
        predicted_categories={f: dict(Counter(r[f] for r in rows)) for f in fields},
        elapsed_s=time.time() - started,
        additional_api_cost_usd=0,
        limitations=[
            "Retrospective development replay after V5 inspection",
            "Typed obligations differ from V5 rubric and original capture schema",
            "Paired views/properties dependent; descriptive only",
            "No new model run or independent adjudication",
        ],
    )
    write(output / "rows.json", rows)
    write(output / "summary.json", summary)
    write(output / "typed-gaps.json", gaps)
    if inventory(source) != before or any(sha(Path(p)) != h for p, h in archives.items()):
        raise ValueError("Predecessor preservation failed")
    frozen = read(output / "freeze.json")
    if inventory(output / "code") != frozen["code"]:
        raise ValueError("Replay code changed during scoring")
    write(
        output / "preservation.json",
        dict(
            passed=True,
            v5_file_count=len(before),
            archives=archives,
            code_verified=True,
            time=time.time(),
        ),
    )
    print({f: summary["metrics"][f]["f1_relative_to_ai"] for f in fields})
    print(dict(output=str(output), failures=failures, elapsed_s=summary["elapsed_s"]))
    if failures:
        raise RuntimeError("Processing failures retained; do not treat as complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.output)
