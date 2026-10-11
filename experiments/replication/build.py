"""Assemble a local, non-overwriting decision-evidence replication deposit candidate."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from pathlib import Path

from .reproduce import sha, write

REPO = Path(__file__).resolve().parents[2]
SECRET = re.compile(
    rb"(?:sk-or-v1-[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)


def copy_tree(source, destination):
    def ignored(directory, names):
        return [
            n
            for n in names
            if n in {"__pycache__", ".DS_Store", "out", ".pytest_cache"}
            or n.endswith((".pyc", ".egg-info"))
        ]

    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("Refuse source tree symlinks: " + source.name)
    shutil.copytree(source, destination, ignore=ignored)


def build(output, preservation, wheelhouse, distributions):
    output = output.resolve()
    archive = output.with_name(output.name + ".zip")
    if output.exists() or archive.exists():
        raise ValueError("Never overwrite a prepared package or archive")
    frozen = json.loads(preservation.read_text())
    for name, digest in frozen["files"].items():
        if sha(REPO / name) != digest:
            raise ValueError("Historical input changed: " + name)
    selected_distributions = [
        distributions / ("decision_trace_reconstructor-0.2.0" + suffix)
        for suffix in ("-py3-none-any.whl", ".tar.gz")
    ]
    for path in selected_distributions:
        if not path.is_file() or path.is_symlink():
            raise ValueError("Missing or unsafe selected distribution: " + str(path))
    output.mkdir(parents=True)
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
        copy_tree(REPO / name, output / name)
    for name in (
        "pyproject.toml",
        "MANIFEST.in",
        "Makefile",
        "CHANGELOG.md",
        "LICENSE",
        ".markdownlint-cli2.jsonc",
        ".pre-commit-config.yaml",
    ):
        shutil.copyfile(REPO / name, output / name)
    metadata = output / "software-metadata"
    metadata.mkdir()
    for name in ("README.md", "CITATION.cff", "codemeta.json", "ro-crate-metadata.json"):
        shutil.copyfile(REPO / name, metadata / name)
    # Copy exact frozen files, including predecessor archives and failed runs.
    for name in frozen["files"]:
        if not name.startswith("study-data/"):
            continue
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, path)
    copy_tree(wheelhouse, output / "wheelhouse")
    if (wheelhouse.parent / "compatibility").exists():
        copy_tree(wheelhouse.parent / "compatibility", output / "compatibility")
    distribution_output = output / "software-distributions"
    distribution_output.mkdir()
    for path in selected_distributions:
        shutil.copyfile(path, distribution_output / path.name)
    for name in ("requirements-replay.txt", "runtime-environment.json"):
        shutil.copyfile(wheelhouse.parent / name, output / name)
    shutil.copyfile(REPO / "docs/replication-study.md", output / "README.md")
    (output / "reproduce.py").write_text(
        "from experiments.replication.reproduce import main\n"
        "if __name__ == '__main__':\n    main()\n"
    )
    (output / "CITATION.cff").write_text(
        'cff-version: 1.2.0\nmessage: "Unpublished deposit candidate; no DOI or publication date assigned. Cite the exact published version after deposit. Historical software citations are in software-metadata/."\n'
        'type: dataset\ntitle: "Decision Trace Reconstructor: frozen V5 assessments, typed evidence contract and retrospective replay"\n'
        'version: "1.0.0"\nlicense: Apache-2.0\n'
        "authors:\n  - family-names: Solozobov\n    given-names: Oleg\n"
        '    orcid: "https://orcid.org/0009-0009-0105-7459"\n'
    )
    write(
        output / "zenodo-metadata-draft.json",
        {
            "status": "local preparation; not an API request; not published",
            "title": "Decision Trace Reconstructor: frozen V5 assessments, typed evidence contract and retrospective replay",
            "version": "1.0.0",
            "resource_type": "dataset",
            "license": "Apache-2.0",
            "creators": [{"name": "Solozobov, Oleg", "orcid": "0009-0009-0105-7459"}],
            "description": "36 sandbox trajectories, 72 retained full/reduced packets, frozen model-assisted V5 assessments, ten assessor controls, twenty authored contract cases, historical instruments and an offline replay. Retrospective agreement and development conformance, not independent validation. Failed predecessor runs are retained. DTR 0.2.0 code is an unpublished local preparation.",
            "related_software_concept_doi": "10.5281/zenodo.19851573",
            "historical_instrument_version_doi": "10.5281/zenodo.19851574",
            "new_software_version_doi": None,
            "study_doi": None,
        },
    )
    files = sorted(p for p in output.rglob("*") if p.is_file())
    for p in files:
        if p.name == ".env" or p.suffix == ".env" or SECRET.search(p.read_bytes()):
            raise ValueError("Potential credential material refused: " + str(p.relative_to(output)))
        if p.suffix == ".zip":
            with zipfile.ZipFile(p) as nested:
                for name in nested.namelist():
                    if not name.endswith("/") and SECRET.search(nested.read(name)):
                        raise ValueError("Potential credential in retained archive")
    inventory = {p.relative_to(output).as_posix(): sha(p) for p in files}
    write(
        output / "replication-manifest.json",
        {
            "schema": "dtr-replication-package-v1",
            "version": "1.0.0",
            "publication_status": "unpublished",
            "dtr_prepared_version": "0.2.0",
            "source_head_before_preparation": frozen["head"],
            "source_identity": "working source bytes identified by this inventory; not a committed release",
            "historical_files": frozen["files"],
            "files": inventory,
        },
    )
    inventory["replication-manifest.json"] = sha(output / "replication-manifest.json")
    (output / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(inventory.items()))
    )
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as target:
        for p in sorted(output.rglob("*")):
            if p.is_file():
                target.write(p, p.relative_to(output.parent))
    with zipfile.ZipFile(archive) as saved:
        if saved.testzip() is not None:
            raise ValueError("Archive integrity failed")
    write(
        archive.with_suffix(".delivery.json"),
        dict(
            archive=archive.name,
            sha256=sha(archive),
            bytes=archive.stat().st_size,
            files=len(inventory) + 1,
            historical_files=len(frozen["files"]),
        ),
    )
    print(json.dumps(dict(archive=str(archive), sha256=sha(archive), files=len(inventory) + 1)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preservation", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--distributions", type=Path, required=True)
    args = parser.parse_args()
    build(args.output, args.preservation, args.wheelhouse, args.distributions)


if __name__ == "__main__":
    main()
