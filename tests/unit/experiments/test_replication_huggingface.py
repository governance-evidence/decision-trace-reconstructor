"""Integrity and preservation checks for the derived HF dataset mirror."""

import json
import stat
import zipfile

import pytest

from experiments.replication import huggingface as hf


def population():
    v5, replay, challenge = (f"study-data/{name}" for name in (hf.V5, hf.REPLAY, hf.CHALLENGE))
    original = f"study-data/{hf.ORIGINAL}"
    contents = {"LICENSE": b"license\n", "docs/evidence-contract.md": b"contract\n"}

    def put(path, value):
        contents[path] = hf.encoded(value)

    index = [
        {"packet_id": pid, "run_id": "main-R1-01", "condition": condition}
        for pid, condition in [("a", "full"), ("b", "A")]
    ]
    put(v5 + "/main-packet-index.json", index)
    put(v5 + "/full-order.json", ["a"])
    put(v5 + "/reduced-order.json", ["b"])
    rows = []
    for entry in index:
        pid = entry["packet_id"]
        put(
            v5 + f"/packets/main/{pid}.json",
            {
                "packet_id": pid,
                "architecture": "single_agent",
                "records": [{"kind": "policy", "id": "r1"}],
            },
        )
        put(
            v5 + f"/assessments/main/{pid}.json",
            {
                "packet_id": pid,
                "assessment": {"questions": {"Q1": {"label": "partially_supported"}}},
            },
        )
        rows.extend(
            {
                **entry,
                "property": prop,
                "reference": "partially_supported",
                "dtr": "structurally_unfillable",
                "exclusion_reasons": [],
            }
            for prop in (
                "inputs",
                "policy_basis",
                "operator_identity",
                "authorization_envelope",
                "output_action",
                "post_condition_state",
            )
        )
    put(v5 + "/scores/rows.json", rows)
    put(replay + "/rows.json", [{**row, "typed": "partially_fillable"} for row in rows])
    put(
        v5 + "/control-gate.json",
        {
            "passed": True,
            "results": [
                {
                    "packet_id": "control",
                    "passed": True,
                    "expected": {"Q1": ["partially_supported"]},
                    "observed": {"Q1": "partially_supported"},
                }
            ],
        },
    )
    put(
        challenge + "/cases.json",
        [
            {"case_id": "positive", "expected_full": True},
            {"case_id": "negative", "expected_full": False},
        ],
    )
    for name in ("protocol.md", "protocol-amendment.md", "study.json", "main-capture-audit.json"):
        contents[original + "/" + name] = b"{}\n"
    contents[original + "/runs/main-R1-01/application-events.jsonl"] = b'{"kind":"policy"}\n'
    contents[original + "/runs/pilot-01/application-events.jsonl"] = b"{}\n"
    contents[v5 + "/budget.json"] = b"{}\n"
    contents[v5 + "/instrument-v0.1.0/code.py"] = b"# preserved in archive\n"
    release = {
        "dataset_id": "dev404ai/dtr-replication",
        "version": "1.0.0",
        "dataset_doi": None,
        "software_doi": "10.5281/zenodo.23297502",
        "archive_name": "fixture.zip",
        "archive_root": "fixture",
        "archive_sha256": "fixture",
        "populations": {
            "trajectories": 1,
            "packets": 2,
            "v5_properties": 12,
            "replay_properties": 12,
            "controls": 1,
            "contract_cases": 2,
        },
    }
    return contents, release, {"README.md": b"card\n", "CITATION.cff": b"type: dataset\n"}


def archive_fixture(tmp_path):
    contents, release, metadata = population()
    files = {p: hf.digest(b) for p, b in contents.items()}
    contents["replication-manifest.json"] = hf.encoded(
        {"files": files, "related_software_version_doi": release["software_doi"]}
    )
    files["replication-manifest.json"] = hf.digest(contents["replication-manifest.json"])
    contents["SHA256SUMS"] = "".join(f"{h}  {p}\n" for p, h in sorted(files.items())).encode()
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "x") as z:
        for name, data in contents.items():
            z.writestr("fixture/" + name, data)
    release["archive_sha256"] = hf.digest(archive.read_bytes())
    return archive, release, metadata


def test_mirror_preserves_bytes_labels_and_existing_outputs(tmp_path):
    archive, release, metadata = archive_fixture(tmp_path)
    original_archive = archive.read_bytes()
    contents = hf.read_archive(archive, release)
    payload, counts = hf.project(contents, release, metadata)
    assert counts == release["populations"]
    mapping = json.loads(payload["data/source-map.json"])["files"]
    for name, item in mapping.items():
        assert payload[name] == contents[item["archive_path"]]
        assert hf.digest(payload[name]) == item["sha256"]
    assert not any("budget" in name or "code.py" in name or "pilot-01" in name for name in payload)
    row = json.loads(payload["data/views/packets-reduced.jsonl"])
    assert row["view"] == "reduced" and row["condition"] == "A"
    assert json.loads(row["assessment_json"])["questions"]["Q1"]["label"] == "partially_supported"
    rows = [json.loads(line) for line in payload["data/views/replay-properties.jsonl"].splitlines()]
    assert len(rows) == 12 and all(row["typed"] == "partially_fillable" for row in rows)
    output = tmp_path / "mirror"
    hf.seal(payload, release, counts)
    assert hf.sync(payload, output) == "prepared"
    mtimes = {p: p.stat().st_mtime_ns for p in output.rglob("*") if p.is_file()}
    assert hf.sync(payload, output) == "unchanged"
    assert hf.sync(payload, output, check=True) == "unchanged"
    assert all(p.stat().st_mtime_ns == value for p, value in mtimes.items())
    assert archive.read_bytes() == original_archive


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "label", "partition", "control"])
def test_population_or_reference_drift_is_refused(mutation):
    contents, release, metadata = population()
    path = f"study-data/{hf.REPLAY}/rows.json"
    rows = json.loads(contents[path])
    if mutation == "duplicate":
        rows[-1] = rows[0]
    elif mutation == "missing":
        rows.pop()
    elif mutation == "label":
        rows[0]["reference"] = "fully_supported"
    elif mutation == "partition":
        contents[f"study-data/{hf.V5}/reduced-order.json"] = hf.encoded(["a"])
    else:
        gate_path = f"study-data/{hf.V5}/control-gate.json"
        gate = json.loads(contents[gate_path])
        gate["passed"] = False
        contents[gate_path] = hf.encoded(gate)
    contents[path] = hf.encoded(rows)
    with pytest.raises(ValueError):
        hf.project(contents, release, metadata)


def test_changed_archive_is_refused(tmp_path):
    archive, release, _ = archive_fixture(tmp_path)
    archive.write_bytes(archive.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="SHA-256"):
        hf.read_archive(archive, release)


@pytest.mark.parametrize("member", ["fixture/../escape", "elsewhere/file", "fixture/link"])
def test_unsafe_archive_member_is_refused_even_with_matching_pin(tmp_path, member):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "x") as z:
        item = zipfile.ZipInfo(member)
        if member.endswith("link"):
            item.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(item, "target")
    with pytest.raises(ValueError, match="Unsafe"):
        hf.read_archive(
            archive, {"archive_sha256": hf.digest(archive.read_bytes()), "archive_root": "fixture"}
        )


@pytest.mark.parametrize("mutation", ["edited", "extra", "symlink"])
def test_existing_local_edits_are_never_overwritten(tmp_path, mutation):
    output = tmp_path / "mirror"
    payload = {"README.md": b"original"}
    hf.sync(payload, output)
    if mutation == "edited":
        (output / "README.md").write_bytes(b"operator edit")
    elif mutation == "extra":
        (output / "notes.md").write_bytes(b"operator notes")
    else:
        (output / "linked").symlink_to(tmp_path / "outside")
    before = (output / "README.md").read_bytes()
    with pytest.raises(ValueError):
        hf.sync(payload, output)
    assert (output / "README.md").read_bytes() == before


def test_empty_clone_metadata_is_preserved(tmp_path):
    output = tmp_path / "clone"
    (output / ".git").mkdir(parents=True)
    (output / ".git/HEAD").write_text("ref: refs/heads/main\n")
    (output / ".gitattributes").write_text("*.parquet filter=lfs\n")
    hf.sync({"README.md": b"card"}, output)
    assert (output / ".git/HEAD").read_text() == "ref: refs/heads/main\n"
    assert (output / ".gitattributes").read_text() == "*.parquet filter=lfs\n"
