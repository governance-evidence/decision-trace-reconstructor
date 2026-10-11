"""Verify exact inputs and reproduce the retained decision-evidence comparisons offline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

V5 = "paper23-20261010-assessor-v5"
REPLAY = "paper23-20261011-typed-replay-v1"
CHALLENGE = "paper23-20261011-evidence-challenge"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inventory(root):
    record = read(root / "replication-manifest.json")
    expected = record["files"]
    for name, digest in expected.items():
        rel = PurePosixPath(name)
        if rel.is_absolute() or ".." in rel.parts or "\\" in name:
            raise ValueError("Unsafe inventory path")
        path = root / name
        if path.is_symlink() or not path.is_file() or sha(path) != digest:
            raise ValueError(f"Inventory mismatch: {name}")
    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    if actual != set(expected) | {"replication-manifest.json", "SHA256SUMS"}:
        raise ValueError("Unexpected or missing package files")
    lines = (root / "SHA256SUMS").read_text().splitlines()
    checksums = {line[66:]: line[:64] for line in lines}
    if checksums != {
        **expected,
        "replication-manifest.json": sha(root / "replication-manifest.json"),
    }:
        raise ValueError("Checksum inventory differs from manifest")
    return record


def equal(actual, expected, label):
    if actual != expected:
        raise ValueError(f"Reproduction differs: {label}")


def no_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.bind"}:
        raise RuntimeError("Network access is forbidden during offline reproduction")


def reproduce(root, output):
    root, output = root.resolve(), output.resolve()
    if output == root or root in output.parents or output.exists():
        raise ValueError("Choose an absent output directory outside the immutable package")
    record = verify_inventory(root)
    os.environ.pop("OPENROUTER_API_KEY", None)
    os.environ.pop("OPENAI_API_KEY", None)
    sys.addaudithook(no_network)
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(root), str(root / "src")]
    output.mkdir(parents=True)
    # This sitecustomize also prevents network operations in child interpreters.
    guard = output / "offline-guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        "import sys, os\nfrom pathlib import Path\n"
        "def block(event, args):\n"
        "    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.bind'}:\n"
        "        raise RuntimeError('Offline reproduction forbids network access')\n"
        "    if event == 'subprocess.Popen' and args[3] is not None:\n"
        "        env = args[3]\n"
        "        env['PYTHONPATH'] = str(Path(__file__).parent) + os.pathsep + env.get('PYTHONPATH', '')\n"
        "sys.addaudithook(block)\n"
    )

    def propagate_guard(event, args):
        if event == "subprocess.Popen" and args[3] is not None:
            child_env = args[3]
            child_env["PYTHONPATH"] = str(guard) + os.pathsep + child_env.get("PYTHONPATH", "")

    sys.addaudithook(propagate_guard)
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join([str(guard), str(root), str(root / "src")]),
    }
    study = root / "study-data"
    v5 = study / V5
    from experiments.paper23_assessor_v5.runner import replay_assessment, verify_control_gate
    from experiments.paper23_assessor_v5.scoring import score
    from experiments.paper23_typed_replay.run import run

    gate = verify_control_gate(v5)
    equal(gate["passed"], True, "V5 control gate")
    for area in ("main", "controls"):
        for audit_path in sorted((v5 / "assessments" / area).glob("*.json")):
            replay_assessment(read(audit_path), read(v5 / "packets" / area / audit_path.name))
    print("Verified 72 retained main assessments and ten controls from raw responses", flush=True)
    score(v5, output / "v5")
    equal(read(output / "v5/rows.json"), read(v5 / "scores/rows.json"), "all 432 V5 rows")
    current = read(output / "v5/summary.json")
    previous = read(v5 / "scores/summary.json")
    for field in previous:
        if field != "elapsed_scoring_s":
            equal(current[field], previous[field], "V5 " + field)
    print("Reproduced the original V5 scores with pinned DTR v0.1.0", flush=True)
    run(v5, output / "typed-replay")
    for name in ("rows.json", "typed-gaps.json"):
        equal(read(output / "typed-replay" / name), read(study / REPLAY / name), name)
    summary = read(output / "typed-replay/summary.json")
    previous = read(study / REPLAY / "summary.json")
    for field in previous:
        if field != "elapsed_s":
            equal(summary[field], previous[field], "typed replay " + field)
    process = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "experiments.paper23_evidence_challenge.run",
            "--study",
            str(study / CHALLENGE),
            "--output",
            str(output / "challenge"),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    write(
        output / "challenge-process.json",
        dict(returncode=process.returncode, stdout=process.stdout, stderr=process.stderr),
    )
    if process.returncode:
        raise RuntimeError("Contract challenge failed; see challenge-process.json")
    challenge = read(output / "challenge/results.json")
    retained = read(study / CHALLENGE / "runs/02/results.json")
    for field in ("summary", "results", "all_property_predictions"):
        equal(challenge[field], retained[field], "20-case challenge " + field)
    table = output / "comparison.csv"
    with table.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["instrument", "tp", "fp", "fn", "tn", "f1_relative_to_ai"])
        for instrument, values in summary["metrics"].items():
            tp = values["precision_relative_to_ai"]["numerator"]
            fp = values["predicted_sufficient"] - tp
            fn = values["reference_sufficient"] - tp
            tn = values["assessable"] - tp - fp - fn
            writer.writerow([instrument, tp, fp, fn, tn, values["f1_relative_to_ai"]["value"]])
    verify_inventory(root)
    result = dict(
        passed=True,
        package_version=record["version"],
        historical_files_unchanged=True,
        main_packets=72,
        property_rows=432,
        v5_controls=10,
        contract_cases=20,
        original_v5_rows_exact=True,
        replay_rows_exact=True,
        replay_metrics_exact=True,
        challenge_predictions_exact=True,
        additional_api_calls=0,
        interpretation="Retrospective agreement and authored conformance; not independent validation",
    )
    write(output / "verification.json", result)
    print(json.dumps(result, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reproduce(args.root, args.output)


if __name__ == "__main__":
    main()
