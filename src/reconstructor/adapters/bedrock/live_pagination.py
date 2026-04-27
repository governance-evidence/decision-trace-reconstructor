"""AWS pagination helpers for Bedrock live ingest."""

from __future__ import annotations

from contextlib import suppress
from typing import Any


def _collect_paginated(
    client: Any,
    method_name: str,
    items_key: str,
    kwargs: dict[str, Any],
) -> list[dict[str, Any]]:
    method = getattr(client, method_name)
    request = dict(kwargs)
    items: list[dict[str, Any]] = []
    next_token: str | None = None
    seen_tokens: set[str] = set()
    while True:
        if next_token is not None:
            request["nextToken"] = next_token
        else:
            with suppress(KeyError):
                del request["nextToken"]
        response = method(**request)
        items.extend(dict(item) for item in response.get(items_key, []))
        candidate = response.get("nextToken")
        if not candidate or candidate in seen_tokens:
            break
        seen_tokens.add(candidate)
        next_token = candidate
    return items
