"""Run the authorised study; human decisions and labels remain explicit inputs."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import subprocess
import time
from pathlib import Path

from .client import Client, load_key, probe
from .packets import freeze_annotations, prepare
from .runner import decide, run, schedule, source_hash, summary
from .storage import Budget, digest, locked, read, write

INSTRUMENT = "40f72522664964e1a467e75420c4f792465b4046"


def initialise(study, protocol):
    study = Path(study)
    target = study / "study.json"
    if target.exists():
        return read(target)
    text = Path(protocol).read_text()

    def sysctl(name):
        result = subprocess.run(["sysctl", "-n", name], text=True, capture_output=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else "unavailable"

    config = {
        "created": time.time(),
        "study_id": study.name,
        "source_hash": source_hash(),
        "instrument_commit": INSTRUMENT,
        "protocol_sha256": digest(text),
        "pilot": schedule("pilot"),
        "main": schedule("main"),
        "hardware": {
            "cpu": sysctl("machdep.cpu.brand_string"),
            "ram_bytes": sysctl("hw.memsize"),
            "os": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "logical_cpus": os.cpu_count(),
            "pydantic": importlib.metadata.version("pydantic"),
            "local_gpu_used": False,
        },
    }
    study.mkdir(parents=True, exist_ok=True)
    (study / "protocol.md").write_text(text)
    write(target, config)
    Budget(study)
    return {
        "study": str(study),
        "source_hash": config["source_hash"],
        "instrument_commit": INSTRUMENT,
    }


def freeze(study):
    study = Path(study)
    if (study / "protocol-freeze.json").exists():
        raise ValueError("Protocol is already frozen")
    config = read(study / "study.json")
    if config["source_hash"] != source_hash():
        raise ValueError(
            "Pilot source differs from current source; preserve and document a revised pilot"
        )
    states = [read(study / "runs" / s["run_id"] / "checkpoint.json") for s in config["pilot"]]
    if any(s["status"] != "completed" or not s.get("ended") for s in states):
        raise ValueError("All six excluded pilots must finish before the main protocol freeze")
    labels = [study / "annotations" / f"pilot-{p}.frozen.json" for p in ("reduced", "full")]
    if not all(p.exists() for p in labels):
        raise ValueError(
            "Actual pilot annotations and measured annotation times must be frozen first"
        )
    preflight = read(study / "provider-preflight.json")
    if not preflight["credential_verified"]:
        raise ValueError("Resolve provider preflight before freezing")
    value = {
        "frozen": time.time(),
        "source_hash": source_hash(),
        "study_sha256": digest(config),
        "pilot_annotations": {p.name: digest(read(p)) for p in labels},
        "pilot_cost": Budget(study).summary(),
        "main_expenditure_ceiling_usd": 5,
        "instrument_commit": INSTRUMENT,
    }
    write(study / "protocol-freeze.json", value)
    return value


def revise_pilot(study, evidence):
    study = Path(study)
    with locked(study / "execution.lock"):
        if (
            not evidence
            or (study / "protocol-freeze.json").exists()
            or list((study / "runs").glob("main-*"))
        ):
            raise ValueError(
                "Pilot revisions require a reason and are forbidden after the main freeze"
            )
        config = read(study / "study.json")
        revision = config.get("pilot_revision", 1) + 1
        if list((study / "annotations").glob("*.json")):
            raise ValueError("Archive existing pilot forms explicitly before revising")
        record = {
            "time": time.time(),
            "reason": evidence,
            "previous_config": config,
            "new_revision": revision,
            "new_source_hash": source_hash(),
            "budget_retained": Budget(study).summary(),
        }
        write(study / "revisions" / f"pilot-r{revision}.json", record)
        config.update(
            pilot_revision=revision, pilot=schedule("pilot", revision), source_hash=source_hash()
        )
        write(study / "study.json", config)
        return {"pilot_revision": revision, "prior_attempts_preserved": True, "budget_reset": False}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "command",
        choices=[
            "init",
            "probe",
            "run",
            "status",
            "decide",
            "packets",
            "freeze-labels",
            "freeze",
            "revise-pilot",
        ],
    )
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--phase", choices=["pilot", "main"], default="pilot")
    parser.add_argument("--run-id")
    parser.add_argument("--decision", choices=["approve", "deny"])
    parser.add_argument("--evidence")
    parser.add_argument("--pass-name", choices=["reduced", "full"])
    args = parser.parse_args()
    if args.command == "init":
        result = initialise(args.study, args.protocol)
    elif args.command == "probe":
        result = probe(args.study, load_key(args.env_file))
    elif args.command == "status":
        result = {"runs": summary(args.study), "budget": Budget(args.study).summary()}
    elif args.command == "decide":
        if not args.run_id or not args.decision or not args.evidence:
            parser.error("decide requires --run-id, --decision and actual --evidence")
        config = read(args.study / "study.json")
        if args.run_id not in {s["run_id"] for p in ("pilot", "main") for s in config[p]}:
            parser.error("Unknown scheduled run")
        decide(args.study / "runs" / args.run_id, args.decision, args.evidence)
        result = {"decision_recorded": args.run_id}
    elif args.command == "packets":
        result = prepare(args.study, args.phase)
    elif args.command == "freeze-labels":
        result = freeze_annotations(args.study, args.phase, args.pass_name)
    elif args.command == "freeze":
        result = freeze(args.study)
    elif args.command == "revise-pilot":
        result = revise_pilot(args.study, args.evidence)
    else:
        config = read(args.study / "study.json")
        if config["source_hash"] != source_hash():
            raise ValueError("Study source hash changed; no silent continuation")
        if args.phase == "main":
            frozen = read(args.study / "protocol-freeze.json")
            if frozen["source_hash"] != source_hash():
                raise ValueError("Frozen source changed")
        if not (args.study / "provider-preflight.json").exists():
            raise ValueError("Run the provider preflight first")
        client = Client(args.study, load_key(args.env_file))
        specs = [s for s in config[args.phase] if not args.run_id or s["run_id"] == args.run_id]
        if not specs:
            raise ValueError("Requested run is not in this phase")
        for spec in specs:
            result = {
                "run_id": spec["run_id"],
                "status": run(args.study, spec, client),
                "budget": client.budget.summary(),
            }
            print(json.dumps(result), flush=True)
        return
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
