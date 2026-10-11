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
SOFTWARE_DOI = "10.5281/zenodo.23297502"
TITLE = "Decision Trace Reconstructor: frozen V5 assessments and typed evidence replay"
DESCRIPTION = """This replication dataset accompanies Decision Trace Reconstructor (DTR) v0.2.0, published separately at https://doi.org/10.5281/zenodo.23297502. It contains 36 GPT-4.1-mini sandbox trajectories represented by 72 paired full and reduced evidence packets. The tasks cover refunds, procurement and configuration changes across three agent architectures and two deployment arrangements.

The archive preserves the frozen V5 assessments produced with Claude Sonnet 4.6, raw model responses, evidence packets, protocols, original scores, failed predecessor runs and the pinned DTR v0.1.0 instrument. It also contains the typed evidence contract, the retrospective replay of all 72 packets, ten assessor calibration controls, twenty authored contract cases and supporting Operational Evidence Plane compatibility material. The original synthetic evaluation results remain unchanged.

A portable reproduction command checks the file inventory, validates the retained assessments, reproduces the original and updated results for 432 property rows, and compares the control and contract-case outcomes with the saved outputs. Reproduction requires no model calls, credentials or paid API access. Pinned dependencies and an offline wheelhouse are included for CPython 3.14 on macOS arm64; other platforms are not claimed as verified. The source snapshot and locally rebuilt software distributions include post-release citation and packaging updates and are identified by file hashes.

V5 is a model-assisted reference without independent human adjudication. The contract cases are development conformance checks, not a held-out validation set. Paired packets and property rows are dependent, and the typed contract requires evidence bindings absent from many older packets. The results support retrospective agreement analysis and contract conformance, not independent validation or general performance superiority."""
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
        'cff-version: 1.2.0\nmessage: "Cite this dataset using the DOI assigned by the hosting repository. The reference DOI identifies the software dependency, not this dataset."\n'
        f'type: dataset\ntitle: "{TITLE}"\n'
        'version: "1.0.0"\nlicense: Apache-2.0\n'
        "authors:\n  - family-names: Solozobov\n    given-names: Oleg\n"
        '    orcid: "https://orcid.org/0009-0009-0105-7459"\n'
        'references:\n  - type: software\n    title: "Decision Trace Reconstructor"\n'
        f'    version: "0.2.0"\n    doi: "{SOFTWARE_DOI}"\n'
        "    authors:\n      - family-names: Solozobov\n        given-names: Oleg\n",
        encoding="utf-8",
    )
    (output / "ZENODO_TITLE.txt").write_text(TITLE + "\n", encoding="utf-8")
    (output / "ZENODO_DESCRIPTION.md").write_text(DESCRIPTION + "\n", encoding="utf-8")
    write(
        output / "zenodo-metadata-draft.json",
        {
            "status": "local preparation; not an API request; not published",
            "title": TITLE,
            "version": "1.0.0",
            "resource_type": "dataset",
            "license": "Apache-2.0",
            "creators": [{"name": "Solozobov, Oleg", "orcid": "0009-0009-0105-7459"}],
            "description": DESCRIPTION,
            "related_software_concept_doi": "10.5281/zenodo.19851573",
            "historical_instrument_version_doi": "10.5281/zenodo.19851574",
            "new_software_version_doi": SOFTWARE_DOI,
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
            "related_software_version_doi": SOFTWARE_DOI,
            "study_doi": None,
            "software_distributions_origin": "local rebuild with post-release citation and packaging updates; not the published software archive",
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
