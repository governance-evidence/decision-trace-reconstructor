# Hugging Face replication mirror

## Ownership and current state

The intended dataset is `dev404ai/dtr-replication`. The canonical card, dataset citation and immutable archive pin are in `huggingface/`. The projection code is `experiments/replication/huggingface.py`; the portable entry point is `scripts/sync_hf_dtr-replication.sh`.

The local workspace entry point is `/Users/mic/development/agent-runtime-evidence/_huggingface/sync_hf_dtr-replication.sh`. It delegates to the DTR script. The default destination is the adjacent `dtr-replication/` directory. Until the author creates the HF repository separately, that directory is a staging folder, not a Git clone. Preparation never initializes a Git repository or contacts Hugging Face.

This follows the existing mirror ownership pattern: maintain source files in the canonical repository and generate the mirror. The dataset has its own identity; it is not an update to DEMM-Bench or Governance Benchmark Dataset.

## Prepare and check

From the DTR repository:

```bash
bash scripts/sync_hf_dtr-replication.sh
bash scripts/sync_hf_dtr-replication.sh --check
```

The script uses the existing DTR virtual environment and Python's standard library. It reads the exact archive pinned in `huggingface/release.json`, validates all archive members and their inventory, then copies the selected evidence and creates the JSONL views. No model calls are made.

Override paths explicitly when needed:

```bash
DTR_PYTHON=python3 \
DTR_HF_ARCHIVE=/path/to/dtr-replication-1.0.0.zip \
DTR_HF_DESTINATION=/path/to/new-staging-folder \
bash scripts/sync_hf_dtr-replication.sh
```

A destination must be absent, empty, an empty separately created clone containing only `.git` and `.gitattributes`, or an exact match for the generated mirror. Repeating a successful sync is read-only. Any changed or extra file blocks synchronization; the script does not delete files or overwrite local edits. For a later metadata revision or dataset version, prepare a new destination and review the difference before updating the published clone. Existing candidates remain available.

## Verification contract

- The input ZIP must match its pinned SHA-256 and internal inventory.
- The populations must be 36 trajectories, 72 packets, 432 original property rows, 432 replay rows, ten controls and twenty contract cases.
- The full and reduced populations must be disjoint, each with 36 packets.
- Each packet must have six distinct property rows in both result sets.
- Reference labels, run IDs and conditions must match between original and replay rows.
- Copied data retain their exact original bytes; the source map identifies each source archive member.
- The derived views preserve labels and predictions; nested structures are JSON strings for stable tabular loading.
- `CHECKSUMS.sha256` covers the mirror inventory and `HF_MANIFEST.json`.
- Altered source archives, duplicate archive paths, destination symlinks, edited mirrors and unexpected files are refused.

The card uses explicit configurations and splits following the [HF manual configuration contract](https://huggingface.co/docs/hub/datasets-manual-configuration). The actual hosted viewer can be checked only after publication; local preparation does not claim that the Hub has processed it.

## Separate publication step

No commit, push, dataset creation or publication is performed by either script. After authorization, the author can create an empty HF dataset repository and clone it to a separate directory. Point `DTR_HF_DESTINATION` to that clone to populate it, inspect the diff and publish through the usual reviewed Git workflow. Do not run `git init` inside the staging folder.

The full Zenodo archive remains unchanged. When its dataset DOI is assigned, update the canonical card, dataset citation and `release.json` in a new preparation, then synchronize a new candidate. Keep the software DOI `10.5281/zenodo.23297502` as a related software citation. Do not place it in the dataset DOI field.
