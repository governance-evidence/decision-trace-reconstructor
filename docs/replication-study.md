# Decision evidence replication study

Study deposit candidate, version 1.0.0. No study DOI or publication date has been assigned. DTR v0.2.0 software was published on 11 October 2026 at <https://doi.org/10.5281/zenodo.23297502>; that software archive does not contain the frozen study dataset. Earlier local candidates retain their original pre-publication metadata and exact source inventories. Publishing the study is a separate author action.

## Reproduce from a clean unpack

Use Python 3.11 or newer. The verified environment is CPython 3.14 on macOS arm64; `runtime-environment.json` records exact versions. The bundled wheelhouse provides an offline installation for that environment. Other platforms can install the same pinned dependencies from their package index; their binary wheels are not included or claimed as tested.

Create the environment and output directory outside this immutable package:

```bash
python3 -m venv ../dtr-replication-env
../dtr-replication-env/bin/python -m pip install --no-index --find-links wheelhouse -r requirements-replay.txt
../dtr-replication-env/bin/python -B reproduce.py --output ../dtr-reproduced
```

For another platform, replace only the installation command with `../dtr-replication-env/bin/python -m pip install -r requirements-replay.txt`. Reproduction itself makes no model or API requests and needs no credentials. Python network operations are blocked in the parent and child interpreters. It uses paths relative to the unpacked package and refuses an existing output directory or output inside the package.

The command verifies the entire checksum inventory, revalidates all 82 retained assessor responses, recomputes the ten-control gate, executes pinned DTR v0.1.0 on all 72 V5 packets, executes coverage and typed reconstruction on the same 72 packets, and replays the 20 contract cases under all retained instruments. It compares all 432 original rows, all 432 replay rows, metrics and challenge predictions with the saved results. It writes `verification.json`, `comparison.csv` and complete new outputs outside the package. Timing and machine paths are execution metadata and are not expected to match historical values.

## Run map and scientific boundaries

Public documentation and new packages use descriptive names: `replication-study.md`, `experiments.replication` and `dtr-replication-1.0.0.zip`. Historical run directories, frozen instrument modules and identifiers retain their recorded names because the freeze verifies both their paths and their bytes. Earlier packages are preserved; the naming change does not revise observations or results.

| Artifact under `study-data/` | Role |
|---|---|
| `paper23-20261010/` | Original sandbox trajectories, evidence capture, first assessments and provenance. |
| `paper23-20261010-assessor-v2*`, `-v3`, `-v4` | Earlier assessor protocols and failed calibration outcomes, retained as development history. |
| `paper23-20261010-assessor-v5/` | Frozen V5: 72 full/reduced packets from 36 trajectories; ten calibration controls; raw responses, derived assessments, labels, original scores and pinned v0.1.0 instrument. |
| `paper23-20261011-evidence-challenge/` | Twenty authored development cases: ten positive and ten negative target checks; both development runs retained. Run `02` is the final comparison. |
| `paper23-20261011-typed-replay-v1/` | Original retrospective replay, including the adapter audit and both coverage and typed outputs for each packet. |
| `*delivery*`, `*-diagnosis/` | Earlier delivery archives and diagnostic reports, retained byte-for-byte. |

The study uses a model-assisted V5 reference, not independently adjudicated human truth. The twenty authored cases are development conformance requirements, not a held-out validation set. The typed contract asks for bindings absent from many older packets; agreement with V5 is not a common-target accuracy competition. Paired packets and property rows are dependent. Historical absolute paths in frozen metadata are provenance strings; the portable reproduction command does not dereference them.

Expected binary F1 against the retained V5 reference is 0.8186 for original DTR, 0.9975 for repaired coverage and the presence baseline, and 0.5495 for the stricter typed contract. The final authored challenge gives 20/20 typed checks and 10/20 coverage/baseline checks. These are bounded descriptive results, not baseline superiority or independent validation.

The root `results/` directory is separately preserved v0.1.0 synthetic-fixture evidence (140 scenarios and named incidents). Its original DOI is 10.5281/zenodo.19851574. It is not replaced by the live-model study or regenerated with 0.2.0.

## Contents and licensing

`src/`, `experiments/`, `tests/`, documentation and examples form the executable source snapshot. `software-metadata/` retains the software citation and metadata separately from the study's root `CITATION.cff`. `replication-manifest.json` identifies every file, the historical preservation-baseline commit and the related software DOI; the delivered working source is identified by its file hashes, not falsely attributed to that commit. `SHA256SUMS` also covers the manifest. `zenodo-metadata-draft.json` is descriptive draft metadata, not a submitted API payload. `ZENODO_TITLE.txt` and `ZENODO_DESCRIPTION.md` provide the corresponding upload-form text. The root dataset citation references DTR v0.2.0 as software; the software DOI is never assigned to the dataset.

Code and authored study material use the repository's Apache-2.0 license. Preserve existing notices and attribution for any third-party material in historical artifacts. Model responses are retained as experimental observations; they do not establish the truth of their assertions. The data concern fictitious author-operated sandbox actions. No API credential is needed or bundled.

## Maintainer assembly

The separate [Hugging Face mirror procedure](huggingface-replication.md) prepares a data-only view from the exact archived ZIP. Its canonical card and archive pin live in `huggingface/`. The HF preparation does not modify this archive, V5 or previous candidates.

From the DTR checkout, supply the pre-edit preservation inventory, a prepared dependency wheelhouse and the verified software distributions from the same source preparation:

```bash
PYTHONPATH=.:src .venv/bin/python -m experiments.replication.build \
  --preservation /path/to/preservation-before.json \
  --wheelhouse /path/to/wheelhouse \
  --distributions /path/to/verified-distributions \
  --output study-data/dtr-replication-1.0.0
```

Assembly refuses overwritten destinations, changed historical files, symlinks and detected credential material. All historical files named in the preservation inventory are retained; the directory holding the new preparation is excluded to prevent recursive packaging. The builder copies the explicitly selected wheel and source distribution, then creates the ZIP, delivery hash, manifest and checksum inventory. It does not select older distributions from the default `dist/` directory. Verify the actual ZIP in a fresh directory before publication. Keep a failed preparation if verification fails and create a new candidate after repairs.

The software wheel packages `reconstructor`; experiment runners ship in the source distribution and this replication package. Study data are deliberately excluded from the software distributions. Publishing a software wheel alone cannot deliver this study.

`software-distributions/` contains a locally rebuilt DTR 0.2.0 wheel and source distribution with post-release citation and packaging updates. These files have their own checksums and are not claimed to be the exact bytes of the published software archive. Runtime code and frozen instruments remain unchanged. `compatibility/oep/` retains the relevant OEP integration files, separate historical/current expectations and verification evidence. It is an integration excerpt, not a full OEP release. Its source inventory records provenance and file hashes.
