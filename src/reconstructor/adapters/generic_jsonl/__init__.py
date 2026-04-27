"""Generic JSONL fallback adapter."""

from __future__ import annotations

from .common import (
    FollowupRule,
    GenericJsonlIngestOptions,
    GenericJsonlMapping,
    MappingFields,
    StateMutationPredicate,
)
from .io import (
    iter_jsonl_stream,
    iter_records_file,
    load_mapping_file,
    load_records_file,
)
from .pipeline import records_to_fragments, records_to_manifest
from .validation import validate_mapping_file, validate_mapping_sample

__all__ = [
    "FollowupRule",
    "GenericJsonlIngestOptions",
    "GenericJsonlMapping",
    "MappingFields",
    "StateMutationPredicate",
    "iter_jsonl_stream",
    "iter_records_file",
    "load_mapping_file",
    "load_records_file",
    "records_to_fragments",
    "records_to_manifest",
    "validate_mapping_file",
    "validate_mapping_sample",
]
