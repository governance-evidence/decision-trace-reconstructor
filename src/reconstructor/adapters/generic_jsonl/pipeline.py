"""Generic JSONL records-to-manifest conversion pipeline."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment, FragmentKind
from ...core.manifest import manifest_dict
from .common import (
    GenericJsonlIngestOptions,
    GenericJsonlMapping,
    _coerce_records,
)
from .fragments import _records_to_fragment_dicts, _serialise_fragment_dict


def records_to_fragments(
    records: list[tuple[int, dict[str, Any]]] | list[dict[str, Any]],
    mapping: GenericJsonlMapping,
    opts: GenericJsonlIngestOptions | None = None,
) -> list[Fragment]:
    cfg = opts or GenericJsonlIngestOptions()
    normalised = _coerce_records(records)
    fragment_dicts = _records_to_fragment_dicts(normalised, mapping, cfg)
    return [Fragment.from_dict(item) for item in fragment_dicts]


def records_to_manifest(
    records: list[tuple[int, dict[str, Any]]] | list[dict[str, Any]],
    mapping: GenericJsonlMapping,
    scenario_id: str,
    opts: GenericJsonlIngestOptions | None = None,
) -> dict[str, Any]:
    cfg = opts or GenericJsonlIngestOptions()
    normalised = _coerce_records(records)
    fragment_dicts = _records_to_fragment_dicts(normalised, mapping, cfg)
    architecture = _infer_architecture(fragment_dicts, mapping, cfg)
    stack_tier = cfg.stack_tier or mapping.stack_tier_default
    fragments = [Fragment.from_dict(_serialise_fragment_dict(item)) for item in fragment_dicts]
    return manifest_dict(
        scenario_id=scenario_id,
        architecture=architecture,
        stack_tier=stack_tier,
        fragments=fragments,
    )


def _infer_architecture(
    fragment_dicts: list[dict[str, Any]],
    mapping: GenericJsonlMapping,
    opts: GenericJsonlIngestOptions,
) -> str:
    if opts.architecture is not None:
        return opts.architecture
    if mapping.architecture != "auto":
        return mapping.architecture
    if any(
        fragment["kind"] in {FragmentKind.HUMAN_APPROVAL.value, FragmentKind.HUMAN_REJECTION.value}
        for fragment in fragment_dicts
    ):
        return "human_in_the_loop"
    actors = {str(fragment["actor_id"]) for fragment in fragment_dicts}
    if len(actors) >= 2:
        return "multi_agent"
    return "single_agent"
