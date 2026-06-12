"""Shared payload summarization helpers for adapter fragment builders."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def content_field(content: Any, keep_raw: bool) -> Any:
    """Return *content* unchanged when *keep_raw*, else a sha256/length summary."""
    if content is None:
        return None
    if keep_raw:
        return content
    encoded = content if isinstance(content, str) else json.dumps(content, sort_keys=True)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return {"sha256": digest, "length": len(encoded)}
