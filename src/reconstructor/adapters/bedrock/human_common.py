"""Shared Bedrock human approval helpers."""

from __future__ import annotations

import json
from typing import Any


def _is_human_approval(result: Any) -> bool:
    if isinstance(result, dict):
        if "approved" in result:
            return bool(result["approved"])
        text = json.dumps(result, sort_keys=True).lower()
        return not any(token in text for token in ("reject", "denied", "deny", "false"))
    if isinstance(result, list):
        return all(_is_human_approval(item) for item in result)
    return "reject" not in str(result).lower()
