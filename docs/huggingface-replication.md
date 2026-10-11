# Hugging Face replication mirror

## Ownership and current state

The intended dataset is `dev404ai/dtr-replication`. The canonical card, dataset citation and immutable archive pin are in `huggingface/`. The projection code is `experiments/replication/huggingface.py`; the portable entry point is `scripts/sync_hf_dtr-replication.sh`.

The local workspace entry point is `/Users/mic/development/agent-runtime-evidence/_huggingface/sync_hf_dtr-replication.sh`. It delegates to the DTR script. The default destination is the adjacent `dtr-replication/` directory. That directory is a staging folder, not a Git clone. Creating an HF repository or uploading through the CLI does not change its local type. Preparation never initializes a Git repository or contacts Hugging Face.

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

No commit, push, dataset creation or publication is performed by either sync script. The operator runs the commands below after approving the exact candidate. They publish only the prepared mirror, without modifying V5, original results, prior archives or either existing benchmark mirror.

The following commands were checked against `hf` 1.17.0 on 2026-10-11. See the [HF CLI documentation](https://huggingface.co/docs/huggingface_hub/en/guides/cli). Use `hf auth whoami` to confirm the intended account, `dev404ai`; if authentication is missing, run `hf auth login` interactively.

From the DTR repository, publish the initial prepared snapshot:

```bash
(
  set -e
  bash scripts/sync_hf_dtr-replication.sh --check
  hf repos create dev404ai/dtr-replication --type dataset --public
  hf upload dev404ai/dtr-replication \
    /Users/mic/development/agent-runtime-evidence/_huggingface/dtr-replication . \
    --type dataset --revision main \
    --commit-message "feat: add DTR replication dataset"
)
```

The subshell stops on any failure. Repository creation deliberately omits `--exist-ok`: if the repository already exists, inspect its current revision and contents before deciding whether to resume the upload. Do not bypass that condition with a deletion or forced push. The upload makes an HF commit; it does not commit or push any GitHub source checkout. No local Git initialization is needed.

A separate HF clone remains an alternative for operators who prefer Git review. Create it at a new path, populate it with `DTR_HF_DESTINATION`, review its diff and publish explicitly. Do not initialize or replace the preserved staging folder.

## Verify the published revision

Save the upload's commit URL and read its exact SHA:

```bash
hf datasets info dev404ai/dtr-replication --expand sha,private,cardData --json
hf datasets parquet dev404ai/dtr-replication --json
```

The first command establishes repository metadata. The second checks availability of viewer-generated Parquet files; it does not by itself prove row counts or correct rendering. Processing may still be pending after the upload. Do not call an unprocessed view verified.

Open the [card](https://huggingface.co/datasets/dev404ai/dtr-replication) and each view below. Check rendered prose, metadata and links; confirm the license and the distinction between the software DOI and the dataset's archival DOI. The approved initial card records its local preparation state; publication evidence belongs to the returned HF revision and its verification record. Any later card wording change is a new candidate requiring its own text audit.

| Configuration | Split | Expected rows | Viewer |
| --- | --- | ---: | --- |
| `packets` | `full` | 36 | [full packets](https://huggingface.co/datasets/dev404ai/dtr-replication/viewer/packets/full) |
| `packets` | `reduced` | 36 | [reduced packets](https://huggingface.co/datasets/dev404ai/dtr-replication/viewer/packets/reduced) |
| `v5_properties` | `evaluation` | 432 | [V5 properties](https://huggingface.co/datasets/dev404ai/dtr-replication/viewer/v5_properties/evaluation) |
| `replay_properties` | `evaluation` | 432 | [replay properties](https://huggingface.co/datasets/dev404ai/dtr-replication/viewer/replay_properties/evaluation) |
| `assessor_controls` | `calibration` | 10 | [assessor controls](https://huggingface.co/datasets/dev404ai/dtr-replication/viewer/assessor_controls/calibration) |
| `contract_cases` | `development` | 20 | [contract cases](https://huggingface.co/datasets/dev404ai/dtr-replication/viewer/contract_cases/development) |

Inspect sample records from every split against its local JSONL view. Nested evidence is intentionally encoded in `*_json` string columns. The full/reduced splits are paired evidence views, not training and test partitions. The [HF splits API](https://huggingface.co/docs/dataset-viewer/en/splits) and [size API](https://huggingface.co/docs/dataset-viewer/en/size) can corroborate configurations, splits and row counts; correlate their dataset revision with the uploaded SHA.

For byte verification, download that exact revision with `hf download`, `--type dataset`, `--revision <uploaded-sha>` and a fresh `--local-dir` outside the preserved staging folder. From the download directory run `shasum -a 256 -c CHECKSUMS.sha256`. Compare its `README.md` and `HF_MANIFEST.json` hashes with the approved local candidate. Hub-generated metadata and local download cache files are not part of the pinned source inventory.

Record the uploaded SHA, verification time, card observations, all six view counts, sample comparisons and checksum outcome. Publication remains distinct from hosted-viewer verification until these checks pass.

## Later archival DOI adoption

The full Zenodo archive remains unchanged. When its dataset DOI is assigned, update the canonical card, dataset citation and `release.json` in a new preparation, then synchronize a new candidate. Keep the software DOI `10.5281/zenodo.23297502` as a related software citation. Do not place it in the dataset DOI field.
