"""LangSmith run-to-fragment mapping dispatch."""

from __future__ import annotations

from typing import Any

from ...core.fragment import Fragment
from .common import LangSmithIngestOptions
from .fragment_builders import (
    _chain_or_prompt_fragment,
    _config_fragment,
    _error_fragment,
    _llm_fragment,
    _policy_fragment,
    _retriever_fragment,
    _tool_fragments,
)
from .fragment_common import _run_fragment_context
from .fragment_predicates import _has_any_tag


def _run_to_fragments(
    run: dict[str, Any],
    opts: LangSmithIngestOptions,
) -> list[Fragment]:
    """Map one normalised LangSmith run to zero or more the reconstructor fragments."""
    ctx = _run_fragment_context(run, opts)
    if ctx.run_type in opts.skip_run_types:
        return []

    # Operator-supplied policy / config snapshots take precedence over
    # run_type-based mapping, because they encode operator intent.
    if _has_any_tag(run, opts.policy_snapshot_tags):
        return [_policy_fragment(ctx)]

    if _has_any_tag(run, opts.config_snapshot_tags):
        return [_config_fragment(ctx)]

    out: list[Fragment] = []
    if ctx.run_type == "llm":
        out.append(_llm_fragment(ctx))

    elif ctx.run_type == "tool":
        out.extend(_tool_fragments(ctx))

    elif ctx.run_type == "retriever":
        out.append(_retriever_fragment(ctx))

    elif ctx.run_type in ("chain", "prompt"):
        out.append(_chain_or_prompt_fragment(ctx))

    # Errors are emitted alongside whatever the primary fragment is, with a
    # 1ms delay to preserve temporal ordering.
    if run.get("error"):
        out.append(_error_fragment(ctx))

    return out
