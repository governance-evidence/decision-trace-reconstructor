#!/usr/bin/env bash
# Prepare or verify a local data mirror. No network, Git writes, or inference.
set -euo pipefail
REPO=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON=${DTR_PYTHON:-"$REPO/.venv/bin/python"}
ARCHIVE=${DTR_HF_ARCHIVE:-"$REPO/study-data/replication-zenodo-preparation-20261011/dtr-replication-1.0.0.zip"}
DESTINATION=${DTR_HF_DESTINATION:-"$(dirname -- "$(dirname -- "$REPO")")/agent-runtime-evidence/_huggingface/dtr-replication"}
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO"
exec "$PYTHON" -B -m experiments.replication.huggingface \
  --archive "$ARCHIVE" --output "$DESTINATION" "$@"
