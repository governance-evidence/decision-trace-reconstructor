"""OTLP adapter conversion pipeline."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from ...core.fragment import Fragment, FragmentKind
from ...core.manifest import manifest_dict
from .common import OtlpIngestOptions, _get_attr, _operation_name
from .fragments import _span_to_fragments
from .normalize import normalise_span_record as _normalise_span_record


def spans_to_fragments(
    spans: Iterable[dict[str, Any] | Any],
    opts: OtlpIngestOptions | None = None,
) -> list[Fragment]:
    """Convert normalized OTLP spans to the reconstructor fragments ordered by timestamp."""
    cfg = opts or OtlpIngestOptions()
    normalised = [_normalise_span_record(span) for span in spans]
    _validate_sampling(normalised, cfg)
    normalised.sort(key=lambda span: (span["start_time_unix_nano"], span["span_id"]))

    out: list[Fragment] = []
    for span in normalised:
        out.extend(_span_to_fragments(span, cfg))

    out.sort(key=lambda frag: (frag.timestamp, frag.fragment_id))
    return out


def spans_to_manifest(
    spans: Iterable[dict[str, Any] | Any],
    scenario_id: str,
    opts: OtlpIngestOptions | None = None,
) -> dict[str, Any]:
    """Build a fragments-manifest dict ready for ``decision-trace reconstruct``."""
    cfg = opts or OtlpIngestOptions()
    normalised = [_normalise_span_record(span) for span in spans]
    _validate_sampling(normalised, cfg)
    fragments = spans_to_fragments(normalised, cfg)
    architecture = _infer_architecture(normalised, cfg, fragments)
    return manifest_dict(
        scenario_id=scenario_id,
        architecture=architecture,
        stack_tier=cfg.stack_tier,
        fragments=fragments,
    )


def _validate_sampling(spans: Sequence[dict[str, Any]], opts: OtlpIngestOptions) -> None:
    if opts.accept_sampled:
        return
    rate = _sampling_rate(spans, opts)
    if rate is not None and rate < 0.5:
        raise ValueError(
            f"OTLP trace appears sampled at rate {rate:.3f}; pass accept_sampled=True to override"
        )


def _sampling_rate(spans: Sequence[dict[str, Any]], opts: OtlpIngestOptions) -> float | None:
    if opts.sampling_rate is not None:
        return opts.sampling_rate
    for span in spans:
        for key in ("otel.trace.sample_rate", "sampling.priority", "sampling.rate"):
            value = _get_attr(span, key)
            if value is None:
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            return numeric
    return None


def _infer_architecture(
    spans: Sequence[dict[str, Any]],
    opts: OtlpIngestOptions,
    fragments: Sequence[Fragment],
) -> str:
    if not opts.auto_architecture:
        return opts.architecture
    if any(
        fragment.kind in {FragmentKind.HUMAN_APPROVAL, FragmentKind.HUMAN_REJECTION}
        for fragment in fragments
    ):
        return "human_in_the_loop"

    actor_ids = {
        str(_get_attr(span, "gen_ai.agent.id"))
        for span in spans
        if _get_attr(span, "gen_ai.agent.id") is not None
    }
    if len(actor_ids) >= 2:
        return "multi_agent"

    by_id = {span["span_id"]: span for span in spans}
    for span in spans:
        if _operation_name(span) != "invoke_agent":
            continue
        parent = by_id.get(span.get("parent_span_id") or "")
        if parent is None:
            continue
        if _get_attr(span, "gen_ai.agent.id") != _get_attr(parent, "gen_ai.agent.id"):
            return "multi_agent"
    return opts.architecture


__all__ = ["spans_to_fragments", "spans_to_manifest"]
