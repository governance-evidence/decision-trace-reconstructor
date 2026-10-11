"""Prepare a data-only HF mirror from an exact, immutable replication ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import tempfile
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

from .build import SECRET
from .reproduce import CHALLENGE, REPLAY, V5

REPO = Path(__file__).resolve().parents[2]
ORIGINAL = "paper23-20261010"
MANIFEST = "HF_MANIFEST.json"
CHECKSUMS = "CHECKSUMS.sha256"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or str(path) != name:
        raise ValueError("Unsafe archive path: " + name)
    return path


def read_archive(archive, release):
    if archive.is_symlink() or digest(archive.read_bytes()) != release["archive_sha256"]:
        raise ValueError("Replication archive SHA-256 differs from the release pin")
    root = release["archive_root"]
    contents = {}
    with zipfile.ZipFile(archive) as source:
        for item in source.infolist():
            path = safe_path(item.filename.rstrip("/"))
            if path.parts[0] != root or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("Unsafe archive root or symlink")
            if item.is_dir():
                continue
            name = str(path.relative_to(root))
            if name in contents:
                raise ValueError("Duplicate archive member: " + name)
            contents[name] = source.read(item)
    manifest = json.loads(contents["replication-manifest.json"])
    expected = manifest["files"]
    if set(contents) != set(expected) | {"replication-manifest.json", "SHA256SUMS"}:
        raise ValueError("Archive population differs from its manifest")
    for name, expected_hash in expected.items():
        if digest(contents[name]) != expected_hash:
            raise ValueError("Archive file differs from manifest: " + name)
    checksums = "".join(
        f"{h}  {name}\n"
        for name, h in sorted(
            {
                **expected,
                "replication-manifest.json": digest(contents["replication-manifest.json"]),
            }.items()
        )
    ).encode()
    if contents["SHA256SUMS"] != checksums:
        raise ValueError("Archive checksum inventory differs")
    if manifest["related_software_version_doi"] != release["software_doi"]:
        raise ValueError("Related software DOI differs")
    return contents


def project(contents, release, metadata):
    """Copy frozen evidence byte-for-byte and add explicitly derived JSONL views."""
    payload = dict(metadata)
    mapping = {}

    def copy(source, target):
        payload[target] = contents[source]
        mapping[target] = {"archive_path": source, "sha256": digest(contents[source])}

    def read(name):
        return json.loads(contents[name])

    v5, replay, challenge = (f"study-data/{name}" for name in (V5, REPLAY, CHALLENGE))
    original = f"study-data/{ORIGINAL}"
    index = read(v5 + "/main-packet-index.json")
    packet_ids = {row["packet_id"] for row in index}
    run_ids = {row["run_id"] for row in index}
    originals = read(v5 + "/scores/rows.json")
    updated = read(replay + "/rows.json")
    gate = read(v5 + "/control-gate.json")
    cases = read(challenge + "/cases.json")
    populations = {
        "trajectories": len(run_ids),
        "packets": len(index),
        "v5_properties": len(originals),
        "replay_properties": len(updated),
        "controls": len(gate["results"]),
        "contract_cases": len(cases),
    }
    if populations != release["populations"] or len(packet_ids) != len(index):
        raise ValueError("Unexpected or duplicate evidence population")
    for rows in (originals, updated):
        keys = {(row["packet_id"], row["property"]) for row in rows}
        counts = Counter(row["packet_id"] for row in rows)
        if len(keys) != len(rows) or set(counts) != packet_ids or set(counts.values()) != {6}:
            raise ValueError("Property rows must cover six distinct properties per packet")
    by_key = {(r["packet_id"], r["property"]): r for r in originals}
    for row in updated:
        prior = by_key.get((row["packet_id"], row["property"]))
        if prior is None or any(row[k] != prior[k] for k in ("reference", "run_id", "condition")):
            raise ValueError("Replay changed a frozen reference or packet identity")
    full = set(read(v5 + "/full-order.json"))
    reduced = set(read(v5 + "/reduced-order.json"))
    if full & reduced or full | reduced != packet_ids or len(full) != len(reduced):
        raise ValueError("Full and reduced packet partitions differ")
    if not gate["passed"] or not all(row["passed"] for row in gate["results"]):
        raise ValueError("Assessor control gate did not pass")
    if len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate authored contract case")

    v5_roots = {
        "protocol.md",
        "freeze.json",
        "instrument-manifest.json",
        "main-packet-index.json",
        "full-order.json",
        "reduced-order.json",
        "control-expectations.json",
        "control-gate.json",
        "question-transitions.json",
        "comparison.json",
        "run.json",
        "closeout-verification.json",
    }
    replay_roots = {
        "PROTOCOL.md",
        "freeze.json",
        "rows.json",
        "summary.json",
        "typed-gaps.json",
        "original-v5-rows.json",
    }
    challenge_roots = {"PROTOCOL.md", "input-freeze.json", "cases.json", "closeout.json"}
    run_files = {
        "application-events.jsonl",
        "service-events.jsonl",
        "checkpoint.json",
        "factual-reference.json",
        "service-state.json",
    }
    for source in sorted(contents):
        if source.startswith(v5 + "/"):
            rel = source[len(v5) + 1 :]
            if rel in v5_roots or rel.split("/")[0] in {
                "packets",
                "assessments",
                "annotations",
                "scores",
                "transport",
            }:
                copy(source, "data/v5/" + rel)
        elif source.startswith(replay + "/"):
            rel = source[len(replay) + 1 :]
            if rel in replay_roots or rel.startswith("packets/"):
                copy(source, "data/typed-replay/" + rel)
        elif source.startswith(challenge + "/"):
            rel = source[len(challenge) + 1 :]
            if rel in challenge_roots or rel in {
                "runs/01/results.json",
                "runs/02/results.json",
                "runs/01/code-freeze.json",
                "runs/02/code-freeze.json",
            }:
                copy(source, "data/contract-cases/" + rel)
        elif source.startswith(original + "/runs/"):
            rel = source[len(original) + 6 :]
            parts = rel.split("/")
            if len(parts) == 2 and parts[0] in run_ids and parts[1] in run_files:
                copy(source, "data/trajectories/" + rel)
    for name in ("protocol.md", "protocol-amendment.md", "study.json", "main-capture-audit.json"):
        copy(original + "/" + name, "data/trajectories/" + name)
    copy("LICENSE", "LICENSE")
    copy("docs/evidence-contract.md", "EVIDENCE_CONTRACT.md")

    def jsonl(name, rows):
        # Nested, heterogeneous records remain JSON strings to keep a stable viewer schema.
        flat = [
            {
                (k + "_json" if isinstance(v, (dict, list)) else k): (
                    json.dumps(v, sort_keys=True, ensure_ascii=False)
                    if isinstance(v, (dict, list))
                    else v
                )
                for k, v in row.items()
            }
            for row in rows
        ]
        payload["data/views/" + name + ".jsonl"] = b"".join(
            (json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n").encode() for row in flat
        )

    packets = []
    for entry in index:
        pid = entry["packet_id"]
        packet_path = f"data/v5/packets/main/{pid}.json"
        assessment_path = f"data/v5/assessments/main/{pid}.json"
        packet = json.loads(payload[packet_path])
        assessment = json.loads(payload[assessment_path])
        if packet["packet_id"] != pid or assessment["packet_id"] != pid:
            raise ValueError("Packet and assessment IDs differ")
        if (entry["condition"] == "full") != (pid in full):
            raise ValueError("Packet condition differs from frozen pass order")
        packets.append(
            {
                "packet_id": pid,
                "run_id": entry["run_id"],
                "condition": entry["condition"],
                "view": "full" if pid in full else "reduced",
                "architecture": packet["architecture"],
                "record_count": len(packet["records"]),
                "packet_path": packet_path,
                "assessment_path": assessment_path,
                "packet_sha256": digest(payload[packet_path]),
                "packet": packet,
                "assessment": assessment["assessment"],
            }
        )
    for view in ("full", "reduced"):
        jsonl("packets-" + view, [r for r in packets if r["view"] == view])
    jsonl("v5-properties", originals)
    jsonl("replay-properties", updated)
    jsonl("assessor-controls", gate["results"])
    jsonl("contract-cases", cases)
    payload["data/source-map.json"] = encoded(
        {
            "archive_sha256": release["archive_sha256"],
            "files": mapping,
            "note": "Every mapped file is an exact byte copy. data/views/*.jsonl are derived views, not new observations or annotations.",
        }
    )
    for name, data in payload.items():
        safe_path(name)
        if Path(name).suffix not in {".json", ".jsonl", ".md", ".cff", ""} or SECRET.search(data):
            raise ValueError("Unsafe data-only mirror payload: " + name)
    return payload, populations


def seal(payload, release, populations):
    inventory = {name: digest(data) for name, data in sorted(payload.items())}
    payload[MANIFEST] = encoded(
        {
            "schema": "dtr-hf-mirror-v1",
            "dataset_id": release["dataset_id"],
            "version": release["version"],
            "publication_status_at_preparation": "not_published",
            "archive_sha256": release["archive_sha256"],
            "archive_name": release["archive_name"],
            "software_doi": release["software_doi"],
            "dataset_doi": release["dataset_doi"],
            "populations": populations,
            "files": inventory,
        }
    )
    inventory[MANIFEST] = digest(payload[MANIFEST])
    payload[CHECKSUMS] = "".join(f"{h}  {n}\n" for n, h in sorted(inventory.items())).encode()
    return payload


def sync(payload, output, check=False):
    """Never replace an existing file; exact repeated syncs are read-only."""
    if output.is_symlink():
        raise ValueError("Refuse destination symlink")
    if output.exists():
        if not output.is_dir():
            raise ValueError("Destination is not a directory")
        paths = [p for p in output.rglob("*") if ".git" not in p.relative_to(output).parts]
        if any(p.is_symlink() for p in paths):
            raise ValueError("Refuse destination symlink")
        actual = {str(p.relative_to(output)): p.read_bytes() for p in paths if p.is_file()}
        # An empty, separately cloned HF repository can carry its own attributes file.
        actual.pop(".gitattributes", None)
        if actual == payload:
            return "unchanged"
        if check or actual:
            raise ValueError(
                "Existing destination differs; preserve it and choose a fresh destination"
            )
    elif check:
        raise ValueError("Check requires an existing mirror")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".dtr-hf-stage-", dir=output.parent) as temp:
        stage = Path(temp) / "mirror"
        stage.mkdir()
        for name, data in payload.items():
            p = stage / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        if output.exists():
            # The preflight above allowed only empty directories or .git/.gitattributes.
            for name in sorted(payload, key=lambda n: n in {MANIFEST, CHECKSUMS}):
                target = output / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(payload[name])
        else:
            stage.rename(output)
    return "prepared"


def prepare(archive, output, check=False, repo=REPO):
    metadata_root = repo / "huggingface"
    release = json.loads((metadata_root / "release.json").read_text())
    metadata = {name: (metadata_root / name).read_bytes() for name in ("README.md", "CITATION.cff")}
    payload, populations = project(read_archive(archive, release), release, metadata)
    payload = seal(payload, release, populations)
    state = sync(payload, output, check)
    return {
        "status": state,
        "destination": str(output),
        "files": len(payload),
        "bytes": sum(map(len, payload.values())),
        "populations": populations,
        "manifest_sha256": digest(payload[MANIFEST]),
        "archive_sha256": release["archive_sha256"],
        "network_requests": 0,
        "commits": 0,
        "pushes": 0,
        "publications": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--check", action="store_true", help="Compare with existing mirror without writes"
    )
    args = parser.parse_args()
    print(json.dumps(prepare(args.archive, args.output, args.check), indent=2))


if __name__ == "__main__":
    main()
