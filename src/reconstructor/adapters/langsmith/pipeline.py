"""LangSmith offline mapping pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ...core.fragment import Fragment
from ...core.manifest import manifest_dict
from .common import LangSmithIngestOptions
from .fragments import _run_to_fragments
from .runs import _normalise_run


def runs_to_fragments(
    runs: Iterable[dict[str, Any] | Any],
    opts: LangSmithIngestOptions | None = None,
) -> list[Fragment]:
    """Convert a sequence of LangSmith run dicts (or ``Run`` objects) into
    the reconstructor fragments, ordered by start time.

    Accepts either raw dicts (offline mode) or ``langsmith.schemas.Run``
    objects (network mode). Both are normalised to dicts internally.
    """
    cfg = opts or LangSmithIngestOptions()
    normalised = [_normalise_run(r) for r in runs]
    normalised.sort(key=lambda r: r["_ts"])

    fragments: list[Fragment] = []
    for run in normalised:
        fragments.extend(_run_to_fragments(run, cfg))
    return fragments


def runs_to_manifest(
    runs: Iterable[dict[str, Any] | Any],
    scenario_id: str,
    opts: LangSmithIngestOptions | None = None,
) -> dict[str, Any]:
    """Build a complete fragments manifest dict ready for
    ``decision-trace reconstruct`` to consume.
    """
    cfg = opts or LangSmithIngestOptions()
    fragments = runs_to_fragments(runs, cfg)
    return manifest_dict(
        scenario_id=scenario_id,
        architecture=cfg.architecture,
        stack_tier=cfg.stack_tier,
        fragments=fragments,
    )
