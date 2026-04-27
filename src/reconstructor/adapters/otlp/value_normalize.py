"""OTLP attribute, status, and kind normalization helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def _parse_otlp_attributes(items: Sequence[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in items:
        if not isinstance(item, dict) or "key" not in item:
            continue
        out[str(item["key"])] = _otlp_value_to_python(item.get("value"))
    return out


def _otlp_value_to_python(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    scalar_keys = (
        "stringValue",
        "intValue",
        "doubleValue",
        "boolValue",
        "bytesValue",
    )
    for key in scalar_keys:
        if key in value:
            raw = value[key]
            if key == "intValue":
                return int(raw)
            if key == "doubleValue":
                return float(raw)
            return raw
    if "arrayValue" in value:
        arr = value["arrayValue"].get("values", []) if isinstance(value["arrayValue"], dict) else []
        return [_otlp_value_to_python(item) for item in arr]
    if "kvlistValue" in value:
        vals = (
            value["kvlistValue"].get("values", []) if isinstance(value["kvlistValue"], dict) else []
        )
        return _parse_otlp_attributes(vals)
    return value


def _translate_legacy_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    out = dict(attributes)
    for key, value in list(attributes.items()):
        if key.startswith("llm."):
            out.setdefault("gen_ai." + key[4:], value)
    return out


def _normalise_status(status: Any) -> dict[str, Any]:
    if status is None:
        return {"code": "OK", "message": None}
    if isinstance(status, str):
        return {"code": status.replace("STATUS_CODE_", ""), "message": None}
    if not isinstance(status, dict):
        return {"code": "OK", "message": None}
    code = status.get("code", "OK")
    if isinstance(code, str):
        code = code.replace("STATUS_CODE_", "")
    return {
        "code": str(code),
        "message": status.get("message"),
    }


def _normalise_span_kind(kind: Any) -> str:
    if kind is None:
        return "internal"
    if isinstance(kind, int):
        return {
            1: "internal",
            2: "server",
            3: "client",
            4: "producer",
            5: "consumer",
        }.get(kind, "internal")
    raw = str(kind).replace("SPAN_KIND_", "").lower()
    return {
        "internal": "internal",
        "server": "server",
        "client": "client",
        "producer": "producer",
        "consumer": "consumer",
    }.get(raw, raw)
