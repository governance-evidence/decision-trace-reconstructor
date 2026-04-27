"""Payload extraction helpers for Anthropic message fragments."""

from __future__ import annotations

import hashlib
from typing import Any


def _thinking_payload(block: dict[str, Any], store_thinking: bool) -> Any:
    thinking = block.get("thinking")
    if store_thinking:
        return thinking
    text = "" if thinking is None else str(thinking)
    return {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "length": len(text)}


def _user_message_text(content: Any) -> Any:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_blocks: list[Any] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                continue
            if block.get("type") == "text":
                text_blocks.append(block.get("text"))
            else:
                text_blocks.append(block)
        if text_blocks:
            return text_blocks if len(text_blocks) > 1 else text_blocks[0]
    return None


def _extract_cache_control(request: dict[str, Any]) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    system = request.get("system")
    if isinstance(system, list):
        for block in system:
            if isinstance(block, dict) and block.get("cache_control") is not None:
                markers.append({"location": "system", "cache_control": block["cache_control"]})
    for message in request.get("messages") or []:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("cache_control") is not None:
                markers.append(
                    {"location": message.get("role"), "cache_control": block["cache_control"]}
                )
    return markers
