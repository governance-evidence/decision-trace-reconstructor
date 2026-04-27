"""Small YAML subset parser used for Generic JSONL mapping files."""

from __future__ import annotations

import ast
from typing import Any

_YamlLine = tuple[int, str, int]


def parse_simple_yaml(text: str) -> Any:
    lines: list[_YamlLine] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = _strip_yaml_comment(raw_line).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        lines.append((indent, stripped, line_no))
    if not lines:
        return {}
    parsed, index = _parse_yaml_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise ValueError(f"unexpected trailing YAML content at line {lines[index][2]}")
    return parsed


def _parse_yaml_block(
    lines: list[_YamlLine],
    index: int,
    indent: int,
) -> tuple[Any, int]:
    if _is_yaml_list_item(lines[index][1]):
        return _parse_yaml_list(lines, index, indent)
    return _parse_yaml_dict(lines, index, indent)


def _parse_yaml_dict(
    lines: list[_YamlLine],
    index: int,
    indent: int,
) -> tuple[dict[str, Any], int]:
    out: dict[str, Any] = {}
    while index < len(lines):
        line_indent, stripped, line_no = lines[index]
        if line_indent < indent:
            break
        if line_indent != indent:
            raise ValueError(f"unexpected indentation at line {line_no}")
        if _is_yaml_list_item(stripped):
            break
        if ":" not in stripped:
            raise ValueError(f"expected key: value mapping at line {line_no}")
        key, value_text = stripped.split(":", 1)
        key = key.strip()
        value_text = value_text.strip()
        index += 1
        if not value_text:
            if index < len(lines) and lines[index][0] > indent:
                child, index = _parse_yaml_block(lines, index, lines[index][0])
                out[key] = child
            else:
                out[key] = None
            continue
        out[key] = _parse_yaml_scalar(value_text)
    return out, index


def _parse_yaml_list(
    lines: list[_YamlLine],
    index: int,
    indent: int,
) -> tuple[list[Any], int]:
    out: list[Any] = []
    while index < len(lines):
        line_indent, stripped, line_no = lines[index]
        if line_indent < indent:
            break
        if line_indent != indent:
            raise ValueError(f"unexpected indentation at line {line_no}")
        if not _is_yaml_list_item(stripped):
            break
        value_text = stripped[1:].strip()
        index += 1
        if not value_text:
            if index >= len(lines) or lines[index][0] <= indent:
                out.append(None)
                continue
            child, index = _parse_yaml_block(lines, index, lines[index][0])
            out.append(child)
            continue
        out.append(_parse_yaml_scalar(value_text))
    return out, index


def _parse_yaml_scalar(text: str) -> Any:
    lowered = text.lower()
    if lowered == "null":
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_yaml_scalar(part.strip()) for part in inner.split(",")]
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        return ast.literal_eval(text)
    try:
        if any(char in text for char in (".", "e", "E")):
            return float(text)
        return int(text)
    except ValueError:
        return text


def _is_yaml_list_item(text: str) -> bool:
    return text == "-" or text.startswith("- ")


def _strip_yaml_comment(line: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return line[:index]
    return line


__all__ = ["parse_simple_yaml"]
