"""Pinned DTR execution and descriptive agreement with attributed references."""

from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys
import tarfile
import time
from collections import Counter, defaultdict
from pathlib import Path

from experiments.paper23.__main__ import INSTRUMENT
from experiments.paper23.packets import ROWS, adapt, baseline, crosswalk
from experiments.paper23.storage import digest, read, write

REPO = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def analysis_hashes():
    return {str(p.relative_to(REPO)): sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))}


def freeze_analysis(study):
    study = Path(study)
    target = study / "analysis-freeze.json"
    if target.exists() or (study / "protocol-freeze.json").exists():
        raise ValueError(
            "Analysis is already frozen; corrections need a separately reported version"
        )
    record = {
        "frozen": time.time(),
        "files": analysis_hashes(),
        "instrument_commit": INSTRUMENT,
        "reference_type": "AI assessment, not independent human validation",
        "primary_rows": list(ROWS),
        "boundary_metrics": "omitted; no independently adjudicated boundary reference",
        "uncertainty": "descriptive finite benchmark; no population confidence intervals",
    }
    write(target, record)
    config = read(study / "study.json")
    config["analysis_freeze_sha256"] = digest(record)
    write(study / "study.json", config)
    return {"analysis_frozen": True, "files": len(record["files"])}


def pin_instrument(study):
    study = Path(study)
    root = study / "instrument-v0.1.0"
    manifest_path = study / "instrument-manifest.json"
    if manifest_path.exists():
        record = read(manifest_path)
        if record["commit"] != INSTRUMENT or any(
            sha(root / p) != h for p, h in record["files"].items()
        ):
            raise ValueError("Pinned instrument changed")
        return root
    if root.exists():
        raise ValueError("Incomplete instrument extraction must be reconciled")
    content = subprocess.check_output(["git", "archive", INSTRUMENT, "src/reconstructor"], cwd=REPO)
    root.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(content)) as archive:
        archive.extractall(root, filter="data")
    files = {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*.py"))}
    write(
        manifest_path,
        {
            "commit": INSTRUMENT,
            "archive_sha256": hashlib.sha256(content).hexdigest(),
            "files": files,
        },
    )
    return root


def rate(numerator, denominator):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def metrics(rows, field="dtr"):
    included = [r for r in rows if not r["excluded"]]
    positives = [r for r in included if r[field] == "fully_fillable"]
    reference_full = [r for r in included if r["reference"] == "fully_supported"]
    tp = sum(r["reference"] == "fully_supported" for r in positives)
    fp = len(positives) - tp
    fn = len(reference_full) - tp
    confusion = Counter((r["reference"], r[field]) for r in included)
    return {
        "rows": len(rows),
        "assessable": len(included),
        "excluded": len(rows) - len(included),
        "predicted_sufficient": len(positives),
        "reference_sufficient": len(reference_full),
        "false_sufficient_fraction_relative_to_ai": rate(fp, len(positives)),
        "missed_sufficiency_fraction_relative_to_ai": rate(fn, len(reference_full)),
        "precision_relative_to_ai": rate(tp, tp + fp),
        "recall_relative_to_ai": rate(tp, tp + fn),
        "f1_relative_to_ai": rate(2 * tp, 2 * tp + fp + fn),
        "confusion": [
            {"reference": a, "prediction": b, "count": count}
            for (a, b), count in sorted(confusion.items())
        ],
        "processing_failures": sum(r[field] == "processing_failure" for r in included),
    }


def paired(rows, field="dtr"):
    groups = defaultdict(dict)
    for row in rows:
        groups[(row["run_id"], row["property"])][
            "full" if row["condition"] == "full" else "reduced"
        ] = row
    changed, caught, stable, downgraded = 0, 0, 0, 0
    for pair in groups.values():
        if set(pair) != {"full", "reduced"} or any(r["excluded"] for r in pair.values()):
            continue
        full, reduced = pair["full"], pair["reduced"]
        downgrade = full[field] == "fully_fillable" and reduced[field] != "fully_fillable"
        if full["reference"] == "fully_supported" and reduced["reference"] != "fully_supported":
            changed += 1
            caught += downgrade
        elif full["reference"] == reduced["reference"] == "fully_supported":
            stable += 1
            downgraded += downgrade
    return {
        "deletion_sensitivity_relative_to_ai": rate(caught, changed),
        "unjustified_downgrades_relative_to_ai": rate(downgraded, stable),
    }


def references(study, phase):
    answers = {}
    for pass_name in ("reduced", "full"):
        source = study / "annotations" / f"{phase}-{pass_name}.json"
        frozen = read(source.with_suffix(".frozen.json"))
        if (
            digest(read(source)) != frozen["source_sha256"]
            or digest(frozen["annotations"]) != frozen["source_sha256"]
        ):
            raise ValueError("Frozen reference source changed")
        if frozen["annotations"]["origin"] != "ai_assessed":
            raise ValueError(
                "This scoring version is explicitly scoped to AI reference assessments"
            )
        for item in frozen["annotations"]["packets"]:
            if item["packet_id"] in answers:
                raise ValueError("Duplicate reference packet")
            answers[item["packet_id"]] = item
    return answers


def score(study, phase="main"):
    study = Path(study).resolve()
    # Check references before importing or executing the instrument.
    answers = references(study, phase)
    frozen_analysis = read(study / "analysis-freeze.json")
    if frozen_analysis["files"] != analysis_hashes():
        raise ValueError("Frozen analysis code changed")
    config = read(study / "study.json")
    if config["analysis_freeze_sha256"] != digest(frozen_analysis):
        raise ValueError("Analysis freeze mismatch")
    if phase == "main":
        frozen_protocol = read(study / "protocol-freeze.json")
        if frozen_protocol["study_sha256"] != digest(config):
            raise ValueError("Study configuration changed after the main freeze")
    index = read(study / f"{phase}-packet-index.json")
    population = {r["packet_id"] for r in index}
    if phase == "main" and set(answers) != population:
        raise ValueError("All constructed main packets need frozen references before scoring")
    index = [r for r in index if r["packet_id"] in answers]
    instrument = pin_instrument(study)
    output = study / "scores" / phase
    if output.exists():
        raise ValueError("Preserve earlier scores; do not overwrite or silently rerun")
    output.mkdir(parents=True)
    rows, raw, failures = [], [], []
    began = time.time()
    for entry in index:
        packet_id = entry["packet_id"]
        packet = read(study / "packets" / phase / (packet_id + ".json"))
        if digest(packet) != entry["sha256"]:
            raise ValueError("Packet changed after construction")
        manifest = output / packet_id / "manifest.json"
        write(manifest, adapt(packet))
        started = time.time()
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "reconstructor.cli",
                "reconstruct",
                str(manifest),
                "--out",
                str(manifest.parent),
            ],
            cwd=instrument,
            capture_output=True,
            text=True,
            timeout=45,
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": str(instrument / "src"),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        write(
            manifest.parent / "process.json",
            {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "started": started,
                "ended": time.time(),
                "instrument": INSTRUMENT,
            },
        )
        if result.returncode:
            predictions = {}
            failures.append(packet_id)
        else:
            report = read(manifest.parent / "feasibility.json")
            raw.append(report)
            predictions = {r["property"]: r["category"] for r in report["per_property"]}
        reference = crosswalk(answers[packet_id]["questions"])
        simple = baseline(packet)
        for prop, questions in ROWS.items():
            exclusions = [answers[packet_id]["questions"][q].get("exclusion") for q in questions]
            rows.append(
                {
                    "packet_id": packet_id,
                    "run_id": entry["run_id"],
                    "condition": entry["condition"],
                    "architecture": packet["architecture"],
                    "tier": packet["tier"],
                    "property": prop,
                    "reference": reference[prop],
                    "dtr": predictions.get(prop, "processing_failure"),
                    "baseline": simple[prop],
                    "excluded": any(exclusions),
                    "exclusion_reasons": exclusions,
                }
            )
    groups = {}
    for dimension in ("property", "condition", "architecture", "tier"):
        groups[dimension] = {
            value: metrics([r for r in rows if r[dimension] == value])
            for value in sorted({r[dimension] for r in rows})
        }
    summary = {
        "reference_type": "AI assessed; not independent human ground truth",
        "instrument_commit": INSTRUMENT,
        "phase": phase,
        "packets_scored": len(index) - len(failures),
        "packet_failures": failures,
        "primary_observable_rows": len(rows),
        "dtr": metrics(rows),
        "baseline": metrics(rows, "baseline"),
        "paired_dtr": paired(rows),
        "paired_baseline": paired(rows, "baseline"),
        "breakdowns": groups,
        "opaque_reasoning": [
            {
                "packet_id": r["scenario_id"],
                "verdict": next(
                    (p for p in r["per_property"] if p["property"] == "reasoning_trace"), None
                ),
            }
            for r in raw
        ],
        "elapsed_scoring_s": time.time() - began,
        "cautions": [
            "Dependent rows and paired views are not independent samples",
            "One run per cell does not estimate model stochastic variability",
            "The generator and AI assessor use the same model family",
            "Disagreements need independent human adjudication",
        ],
    }
    write(output / "rows.json", rows)
    write(output / "summary.json", summary)
    write(
        output / "discrepancies.json",
        [
            r
            for r in rows
            if not r["excluded"]
            and ((r["dtr"] == "fully_fillable") != (r["reference"] == "fully_supported"))
        ],
    )
    return {
        "scored_packets": len(index),
        "processing_failures": len(failures),
        "summary": str(output / "summary.json"),
        "reference_type": summary["reference_type"],
    }
