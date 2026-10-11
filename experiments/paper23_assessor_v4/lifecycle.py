"""Immutable predecessors, explicit carry-forward budget and frozen inputs."""

import shutil
import time
from pathlib import Path

from experiments.paper23.client import http_json
from experiments.paper23.storage import read, write
from experiments.paper23_assessor_v3.runner import sha, verify_original
from experiments.paper23_assessor_v3.runner import verify_freeze as verify_v3

from .client import MODEL, PROVIDER

REPO = Path(__file__).resolve().parents[2]


def inventory(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob("*")) if p.is_file()}


def own_hashes():
    files = [
        *sorted((REPO / "experiments").rglob("*.py")),
        *sorted((REPO / "tests/unit/experiments").rglob("*.py")),
    ]
    return {str(p.relative_to(REPO)): sha(p) for p in files}


def prepare(root, predecessor, protocol, key):
    if root.exists():
        raise ValueError("Use a new, absent run directory; preparation must not overwrite")
    verify_v3(predecessor)
    verify_original(predecessor)
    prior = read(predecessor / "run.json")
    # Snapshot every previous version and archive before creating this version.
    previous = {
        str(p.resolve()): inventory(p) if p.is_dir() else sha(p)
        for p in sorted(predecessor.parent.glob("paper23-20261010*"))
    }
    model = next(m for m in http_json("/models", key)["data"] if m["id"] == MODEL)
    account = http_json("/key", key)["data"]
    pricing = model["pricing"]
    if float(pricing["prompt"]) > 3e-6 or float(pricing["completion"]) > 15e-6:
        raise ValueError("Current listed prices exceed the frozen route ceiling")
    root.mkdir()
    write(root / "predecessor-inventory.json", previous)
    write(
        root / "provider-preflight.json",
        {
            "time": time.time(),
            "model": model,
            "credential_verified": True,
            "key_limit_remaining": account.get("limit_remaining"),
        },
    )
    for name in [
        "original-preservation-before.json",
        "main-packet-index.json",
        "control-expectations.json",
        "reduced-order.json",
        "full-order.json",
        "budget.json",
    ]:
        shutil.copyfile(predecessor / name, root / name)
    shutil.copytree(predecessor / "packets", root / "packets")
    shutil.copyfile(protocol, root / "protocol.md")
    budget = read(root / "budget.json")
    if (
        len({r["id"] for r in budget["requests"]}) != len(budget["requests"])
        or budget["cap_usd"] != 5
    ):
        raise ValueError("Invalid carry-forward budget")
    write(
        root / "run.json",
        {
            "created": time.time(),
            "original": prior["original"],
            "predecessor": str(predecessor),
            "model": MODEL,
            "provider": PROVIDER,
            "old_budget_requests": len(budget["requests"]),
            "old_budget_sha256": sha(predecessor / "budget.json"),
            "independent_human_validation": False,
            "control_population": "same ten V3 calibration packets; no independent holdout",
            "analysis_design": "adaptive output-contract follow-up on retained projected packets",
        },
    )
    return {
        "prepared": True,
        "main_packets": len(read(root / "main-packet-index.json")),
        "controls": len(read(root / "control-expectations.json")),
        "prior_requests": len(budget["requests"]),
        "prior_charged_plus_reserved_usd": sum(
            r["charged_or_reserved_usd"] for r in budget["requests"]
        ),
        "model": MODEL,
        "pricing": pricing,
    }


def freeze(root):
    if (root / "freeze.json").exists() or (root / "transport").exists():
        raise ValueError("Do not refreeze a run or freeze after inference")
    files = [
        root / name
        for name in [
            "protocol.md",
            "run.json",
            "provider-preflight.json",
            "predecessor-inventory.json",
            "original-preservation-before.json",
            "main-packet-index.json",
            "control-expectations.json",
            "reduced-order.json",
            "full-order.json",
        ]
    ]
    files += sorted((root / "packets").rglob("*.json"))
    write(
        root / "freeze.json",
        {
            "time": time.time(),
            "code": own_hashes(),
            "inputs": {str(p.relative_to(root)): sha(p) for p in files},
        },
    )
    verify_freeze(root)
    return {"frozen": True, "input_files": len(files), "code_and_test_files": len(own_hashes())}


def verify_freeze(root):
    frozen = read(root / "freeze.json")
    if frozen["code"] != own_hashes() or any(
        sha(root / p) != h for p, h in frozen["inputs"].items()
    ):
        raise ValueError("Frozen V4 code, tests, dependencies or input changed")


def verify_preservation(root):
    verify_freeze(root)
    prior = read(root / "predecessor-inventory.json")
    files = 0
    for path, expected in prior.items():
        path = Path(path)
        actual = inventory(path) if isinstance(expected, dict) else sha(path)
        if actual != expected:
            raise ValueError("Predecessor changed: " + str(path))
        files += len(expected) if isinstance(expected, dict) else 1
    result = verify_original(root)
    return {
        **result,
        "all_predecessor_files_unchanged": files,
        "predecessor_roots_or_archives": len(prior),
        "v4_code_and_inputs_unchanged": True,
    }
