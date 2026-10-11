---
license: apache-2.0
language:
  - en
pretty_name: DTR Replication
tags:
  - decision-evidence
  - agent-evaluation
  - reproducibility
  - synthetic-data
  - model-assisted-assessment
size_categories:
  - n<1K
task_categories:
  - other
configs:
  - config_name: packets
    default: true
    data_files:
      - split: full
        path: data/views/packets-full.jsonl
      - split: reduced
        path: data/views/packets-reduced.jsonl
  - config_name: v5_properties
    data_files:
      - split: evaluation
        path: data/views/v5-properties.jsonl
  - config_name: replay_properties
    data_files:
      - split: evaluation
        path: data/views/replay-properties.jsonl
  - config_name: assessor_controls
    data_files:
      - split: calibration
        path: data/views/assessor-controls.jsonl
  - config_name: contract_cases
    data_files:
      - split: development
        path: data/views/contract-cases.jsonl
---

# DTR Replication: frozen V5 assessments and typed evidence replay

This dataset contains the retained evidence for a controlled Decision Trace Reconstructor (DTR) study: 36 sandbox trajectories, 72 paired full and reduced evidence packets, frozen V5 model-assisted assessments and a retrospective replay with a typed evidence contract. It also includes ten assessor calibration controls and twenty authored contract cases.

The canonical source is [decision-trace-reconstructor](https://github.com/governance-evidence/decision-trace-reconstructor). DTR v0.2.0 software is published at [10.5281/zenodo.23297502](https://doi.org/10.5281/zenodo.23297502). That DOI identifies software; no archival DOI has yet been assigned to this dataset. The intended Hugging Face identifier is `dev404ai/dtr-replication`, version 1.0.0. This card is prepared locally and does not assert that publication has occurred.

## Population and collection

GPT-4.1-mini produced the trajectories in fictitious refund, procurement and configuration sandboxes. Six scenario cards were run under three architectures (single agent, planner/executor and human approval) and two deployment arrangements (within one stack and a separate service process). The author supplied recorded human approval decisions where required. Those approvals are experimental actions, not independent human annotation.

Each trajectory has one full and one reduced packet. The original condition codes are retained: `full`, `A` and `O`. The reduced packets contain controlled evidence deletions. Packet pairs share a trajectory and are statistically dependent; their property rows are also dependent. The `full` and `reduced` splits are evidence views, not training and test partitions.

V5 uses Claude Sonnet 4.6 with deterministic evidence-role eligibility constraints. It retains the raw responses and the accepted assessments. The six observable property rows per packet yield 432 rows. Internal reasoning is outside these six observable properties. The seven question labels in each assessment remain distinct from the six scored property labels; no question is silently relabeled or discarded from the raw record.

## Available configurations

| Configuration | Split | Rows | Purpose |
|---|---|---:|---|
| `packets` | `full` | 36 | Complete retained packet views and their assessments |
| `packets` | `reduced` | 36 | Paired views after controlled deletions |
| `v5_properties` | `evaluation` | 432 | Original DTR and baseline outputs against the V5 reference |
| `replay_properties` | `evaluation` | 432 | Original DTR, repaired coverage, presence baseline and typed outputs |
| `assessor_controls` | `calibration` | 10 | Prespecified assessor expectations and observed outcomes |
| `contract_cases` | `development` | 20 | Ten positive and ten present-but-inadequate authored cases |

The JSONL views are deterministic projections of the frozen files. Columns with the `_json` suffix contain nested values; decode those strings with `json.loads`. This preserves heterogeneous evidence records without inferring a shared nested schema. Original JSON files remain available alongside the views.

For example, after downloading the mirror to `dtr-replication/`:

```python
import json
from pathlib import Path

path = Path("dtr-replication/data/views/packets-full.jsonl")
rows = [json.loads(line) for line in path.read_text().splitlines()]
packet = json.loads(rows[0]["packet_json"])
assessment = json.loads(rows[0]["assessment_json"])
```

## Files and provenance

| Path | Content |
|---|---|
| `data/trajectories/` | Application and service events, checkpoints, factual reference records and collection protocol for the 36 main runs |
| `data/v5/` | Frozen packets, accepted assessments, raw responses, annotations, original scores, protocol and calibration gate |
| `data/typed-replay/` | Saved replay rows, summaries, adapter audits, reconstructed inputs and per-packet outputs |
| `data/contract-cases/` | Authored cases, protocol, input freeze and retained results from both development runs |
| `data/views/` | Six JSONL files used by the configurations above |
| `data/source-map.json` | Original archive path and SHA-256 for each file copied without changing its bytes |
| `EVIDENCE_CONTRACT.md` | Frozen contract documentation from the replication archive |
| `HF_MANIFEST.json` | Mirror inventory, source archive hash, software DOI and population counts |
| `CHECKSUMS.sha256` | Checksums for the mirror files and manifest |

The source archive is `dtr-replication-1.0.0.zip`, SHA-256 `31bd9577bbd6d44c7fb8ae6899d8b2574fa49d262f75864b75c0b5ac6427e96d`. The mirror gives its copied files descriptive paths; their contents remain unchanged. Historical paths inside frozen records are provenance strings, and `data/source-map.json` maps them to archive members. A field named `sha256` inside an old record can identify normalized JSON; it must not be substituted for the byte hashes in the source map.

The mirror omits software distributions, instrument source trees, dependency wheels, credentials and account bookkeeping. Failed assessor predecessors, pilot runs, legacy synthetic results and earlier delivery archives remain preserved in the complete replication archive. Their omission from this focused mirror does not revise or delete them.

To verify a downloaded mirror from its root:

```bash
shasum -a 256 -c CHECKSUMS.sha256
```

Full executable reproduction uses the separate replication archive and its `reproduce.py` entry point. The archive was verified offline on CPython 3.14 and macOS arm64: all 432 original rows, all 432 replay rows, metrics and contract-case predictions matched the saved results. The ten assessor controls passed. Reproduction made no model requests. This data-only mirror does not contain the executable environment.

## Interpretation and limitations

V5 is a model-assisted reference without independent human adjudication. It combines rule-constrained eligibility with model judgments. Earlier calibration failures led to protocol changes, so the ten controls are reused development controls, not an independent holdout. The twenty authored contract cases are development conformance requirements, not a held-out validation set.

The typed contract requires explicit bindings that many older packets do not contain. Agreement with V5 therefore compares different evidence requirements and must not be treated as a common-target accuracy competition. The data support retrospective agreement analysis and contract conformance; they do not establish general performance superiority, production reliability or regulatory compliance.

Model responses are recorded observations and can contain factual errors. The sandbox entities are fictitious. The author participated in collection, protocol development and contract-case design. No independent human annotation study was conducted. Frozen records can contain local machine paths, timestamps and request identifiers as provenance; these are not credentials.

## License and citation

Code and authored study material retain the Apache-2.0 license used by the source package. Preserve any existing third-party notices. The license is not changed to match unrelated datasets in the same account.

Use `CITATION.cff` and pin the exact dataset revision when citing the mirror. The DTR software DOI is a related software citation, not a DOI for these observations. Add the dataset's archival DOI only after the separate deposit has been published.
