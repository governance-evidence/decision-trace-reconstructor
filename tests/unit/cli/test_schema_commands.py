"""CLI tests for schema export and validation failure paths."""

from __future__ import annotations

import json
from pathlib import Path

from reconstructor.cli import main


def test_export_schemas_cli_writes_public_json_schemas(tmp_path: Path) -> None:
    out_dir = tmp_path / "schemas"

    exit_code = main(["export-schemas", "--out", str(out_dir)])

    assert exit_code == 0
    expected = {
        "cells.schema.json",
        "generic_jsonl_mapping.schema.json",
        "named_incidents.schema.json",
        "per_property.schema.json",
        "per_scenario.schema.json",
    }
    assert {path.name for path in out_dir.iterdir()} == expected
    for filename in expected:
        schema = json.loads((out_dir / filename).read_text())
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == f"https://decisiontrace.org/reconstructor/v0.1.0/schemas/{filename}"


def test_validate_generic_jsonl_reports_loader_errors(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    missing_mapping = tmp_path / "missing.yaml"
    sample = tmp_path / "sample.jsonl"
    sample.write_text('{"id": "x"}\n')

    exit_code = main(
        [
            "validate",
            "generic-jsonl",
            "--mapping",
            str(missing_mapping),
            "--sample-from",
            str(sample),
        ]
    )

    assert exit_code == 2
    assert "error:" in capsys.readouterr().err
