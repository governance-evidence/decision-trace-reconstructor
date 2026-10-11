"""Adversarial checks for the portable package integrity boundary."""

import json

import pytest

from experiments.paper23_replication.reproduce import equal, sha, verify_inventory


def fixture(root):
    (root / "data.json").write_text('{"label":"partial"}\n')
    files = {"data.json": sha(root / "data.json")}
    (root / "replication-manifest.json").write_text(json.dumps({"files": files}))
    files["replication-manifest.json"] = sha(root / "replication-manifest.json")
    (root / "SHA256SUMS").write_text("".join(f"{h}  {p}\n" for p, h in files.items()))


def test_valid_package(tmp_path):
    fixture(tmp_path)
    assert verify_inventory(tmp_path)["files"] == {"data.json": sha(tmp_path / "data.json")}


@pytest.mark.parametrize("mutation", ["label", "missing", "extra", "inventory", "checksum"])
def test_modified_packet_or_inventory_is_refused(tmp_path, mutation):
    fixture(tmp_path)
    if mutation == "label":
        (tmp_path / "data.json").write_text('{"label":"full"}\n')
    elif mutation == "missing":
        (tmp_path / "data.json").unlink()
    elif mutation == "extra":
        (tmp_path / "extra.json").write_text("{}")
    elif mutation == "inventory":
        (tmp_path / "replication-manifest.json").write_text('{"files":{"../escape":"hash"}}')
    else:
        (tmp_path / "SHA256SUMS").write_text("")
    with pytest.raises(ValueError):
        verify_inventory(tmp_path)


def test_results_are_compared_exactly():
    with pytest.raises(ValueError, match="Reproduction differs"):
        equal([{"tp": 150}], [{"tp": 151}], "scientific rows")
