"""Tests for Generic JSONL path helpers and compatibility facade."""

from __future__ import annotations

import pytest

from reconstructor.adapters.generic_jsonl import utils as generic_jsonl_utils
from reconstructor.adapters.generic_jsonl.paths import (
    delete_path,
    get_path,
    path_exists,
    set_path,
)
from reconstructor.adapters.generic_jsonl.yaml import parse_simple_yaml


def test_generic_jsonl_utils_facade_exports_focused_helpers() -> None:
    assert set(generic_jsonl_utils.__all__) == {
        "MISSING",
        "delete_path",
        "get_path",
        "parse_simple_yaml",
        "path_exists",
        "set_path",
    }
    assert generic_jsonl_utils.get_path({"a": {"b": 1}}, "a.b") == 1
    assert generic_jsonl_utils.parse_simple_yaml("enabled: true\n") == {"enabled": True}


def test_path_helpers_support_nested_lists_and_noop_mutation() -> None:
    data = {"items": [{"secret": "abc", "name": "first"}]}
    assert get_path(data, "items.0.name") == "first"
    assert path_exists(data, "items.0.secret")

    set_path(data, "items.0.secret", "[REDACTED]")
    assert data["items"][0]["secret"] == "[REDACTED]"

    delete_path(data, "items.0.secret")
    assert not path_exists(data, "items.0.secret")

    set_path(data, "items.bad.name", "ignored")
    delete_path(data, "items.9.name")
    assert data == {"items": [{"name": "first"}]}


def test_get_path_reports_missing_paths_without_default() -> None:
    with pytest.raises(KeyError, match="path 'missing' not found"):
        get_path({}, "missing")
    with pytest.raises(KeyError, match="expected list index"):
        get_path([], "bad")
    with pytest.raises(KeyError, match="index 3 out of range"):
        get_path([], "3")


def test_simple_yaml_parser_handles_comments_quotes_lists_and_nested_blocks() -> None:
    parsed = parse_simple_yaml(
        """
name: "agent #1" # comment
count: 2
enabled: true
empty: null
tags: [alpha, beta]
steps:
  - tool_call
  -
    nested: 1
""".strip()
    )
    assert parsed == {
        "name": "agent #1",
        "count": 2,
        "enabled": True,
        "empty": None,
        "tags": ["alpha", "beta"],
        "steps": ["tool_call", {"nested": 1}],
    }


def test_simple_yaml_parser_reports_structural_errors() -> None:
    with pytest.raises(ValueError, match="expected key: value mapping"):
        parse_simple_yaml("not-a-mapping")
    with pytest.raises(ValueError, match="unexpected indentation"):
        parse_simple_yaml("root:\n    child: 1\n  bad: 2")
