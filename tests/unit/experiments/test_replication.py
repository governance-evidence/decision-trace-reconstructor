"""Adversarial checks for the portable package integrity boundary."""

import json

import pytest

from experiments.replication.reproduce import equal, sha, verify_inventory


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


def build_fixture(tmp_path, monkeypatch):
    from experiments.replication import build as builder

    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(builder, "REPO", repo)
    for name in (
        "src",
        "experiments",
        "tests",
        "docs",
        "examples",
        "scripts",
        "results",
        ".github",
    ):
        (repo / name).mkdir()
    for name in (
        "pyproject.toml",
        "MANIFEST.in",
        "Makefile",
        "CHANGELOG.md",
        "LICENSE",
        ".markdownlint-cli2.jsonc",
        ".pre-commit-config.yaml",
        "README.md",
        "CITATION.cff",
        "codemeta.json",
        "ro-crate-metadata.json",
        "docs/replication-study.md",
    ):
        (repo / name).write_text("fixture\n")
    historical = repo / "study-data/frozen-v5/assessment.json"
    historical.parent.mkdir(parents=True)
    historical.write_text('{"label":"partial"}\n')
    preservation = tmp_path / "preservation.json"
    preservation.write_text(
        json.dumps(
            {"head": "fixture-head", "files": {str(historical.relative_to(repo)): sha(historical)}}
        )
    )
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (tmp_path / "requirements-replay.txt").write_text("fixture\n")
    (tmp_path / "runtime-environment.json").write_text("{}\n")
    distributions = tmp_path / "verified-distributions"
    distributions.mkdir()
    (repo / "dist").mkdir()
    for suffix in ("-py3-none-any.whl", ".tar.gz"):
        name = "decision_trace_reconstructor-0.2.0" + suffix
        (distributions / name).write_bytes(b"selected-current-distribution")
        (repo / "dist" / name).write_bytes(b"older-preserved-distribution")
    return builder, preservation, wheelhouse, distributions, historical


def test_build_selects_current_distributions_and_preserves_frozen_inputs(tmp_path, monkeypatch):
    builder, preservation, wheelhouse, distributions, historical = build_fixture(
        tmp_path, monkeypatch
    )
    before = historical.read_bytes()
    output = tmp_path / "dtr-replication-1.0.0"
    builder.build(output, preservation, wheelhouse, distributions)
    record = verify_inventory(output)
    assert record["schema"] == "dtr-replication-package-v1"
    assert (
        (output / "reproduce.py")
        .read_text()
        .startswith("from experiments.replication.reproduce import main\n")
    )
    metadata = json.loads((output / "zenodo-metadata-draft.json").read_text())
    assert metadata["title"].startswith("Decision Trace Reconstructor:")
    assert metadata["study_doi"] is None
    assert record["study_doi"] is None
    assert metadata["new_software_version_doi"] == record["related_software_version_doi"]
    assert record["related_software_version_doi"] == "10.5281/zenodo.23297502"
    assert (output / "ZENODO_TITLE.txt").read_text() == metadata["title"] + "\n"
    assert (output / "ZENODO_DESCRIPTION.md").read_text() == metadata["description"] + "\n"
    citation = (output / "CITATION.cff").read_text()
    assert "\ndoi:" not in citation
    assert '    doi: "10.5281/zenodo.23297502"' in citation
    for name in ("CITATION.cff", "zenodo-metadata-draft.json", "reproduce.py"):
        assert "paper23" not in (output / name).read_text().lower()
    for path in distributions.iterdir():
        assert (output / "software-distributions" / path.name).read_bytes() == path.read_bytes()
    assert (output / "study-data/frozen-v5/assessment.json").read_bytes() == before
    assert historical.read_bytes() == before
    archive = tmp_path / "dtr-replication-1.0.0.zip"
    archive_hash = sha(archive)
    with pytest.raises(ValueError, match="Never overwrite"):
        builder.build(output, preservation, wheelhouse, distributions)
    assert sha(archive) == archive_hash


def test_missing_selected_distribution_is_refused_before_creating_package(tmp_path, monkeypatch):
    builder, preservation, wheelhouse, distributions, _ = build_fixture(tmp_path, monkeypatch)
    next(distributions.iterdir()).unlink()
    output = tmp_path / "dtr-replication-1.0.0"
    with pytest.raises(ValueError, match="Missing or unsafe selected distribution"):
        builder.build(output, preservation, wheelhouse, distributions)
    assert not output.exists()
