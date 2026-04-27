"""Payload extraction helpers for OTLP GenAI spans."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .common import OtlpIngestOptions, _content_field, _get_attr


def _tool_args(span: dict[str, Any], opts: OtlpIngestOptions) -> Any:
    for key in (
        "gen_ai.tool.call.arguments",
        "gen_ai.tool.arguments",
        "tool.arguments",
    ):
        value = _get_attr(span, key)
        if value is not None:
            return _content_field(value, opts.store_content)
    return None


def _assistant_messages(span: dict[str, Any], opts: OtlpIngestOptions) -> list[Any]:
    messages: list[Any] = []
    for event in span.get("events", []):
        if event.get("name") == "gen_ai.assistant.message":
            content = event.get("attributes", {}).get("content")
            if content is not None:
                messages.append(_content_field(content, opts.store_content))
    return messages


def _tool_result_payload(span: dict[str, Any], opts: OtlpIngestOptions) -> Any:
    for event in span.get("events", []):
        if event.get("name") == "gen_ai.tool.message":
            attrs = event.get("attributes", {})
            if "content" in attrs:
                return _content_field(attrs["content"], opts.store_content)
            return _content_field(attrs, opts.store_content)
    return None


def _extract_media_descriptors(span: dict[str, Any]) -> list[dict[str, Any]]:
    media: list[dict[str, Any]] = []
    for event in span.get("events", []):
        attrs = event.get("attributes", {})
        for key, value in attrs.items():
            lower = key.lower()
            if "image" not in lower and "audio" not in lower and "video" not in lower:
                continue
            encoded = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
            media.append(
                {
                    "type": key,
                    "hash": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
                    "size_bytes": len(encoded.encode("utf-8")),
                }
            )
    return media


def _retrieval_result_from_tool(
    span: dict[str, Any],
    opts: OtlpIngestOptions,
) -> dict[str, Any] | None:
    result = _tool_result_payload(span, opts)
    if not isinstance(result, dict):
        return None
    if any(key in result for key in ("documents", "results", "hits", "retrieved")):
        return {
            "query": _tool_args(span, opts),
            "retrieved": result,
        }
    return None
