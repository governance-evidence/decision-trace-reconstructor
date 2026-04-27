"""Export JSON Schema documents from the Pydantic v2 result models.

Re-run after any change to ``src/reconstructor/output/models.py`` to keep
``docs/schemas/`` in sync. Each result artifact has its own JSON Schema file
named after the artifact it validates.

Usage::

    python scripts/export_schemas.py [--out docs/schemas]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from reconstructor.output.models import (
    CellResults,
    GenericJsonlMappingConfig,
    NamedIncidentResults,
    PerPropertyTable,
    PerScenarioResults,
)

# (artifact filename, root model)
TARGETS = (
    ("cells.schema.json", CellResults),
    ("generic_jsonl_mapping.schema.json", GenericJsonlMappingConfig),
    ("per_property.schema.json", PerPropertyTable),
    ("per_scenario.schema.json", PerScenarioResults),
    ("named_incidents.schema.json", NamedIncidentResults),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/schemas"),
        help="Output directory for JSON Schema files (default: docs/schemas).",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    for filename, model_cls in TARGETS:
        schema = model_cls.model_json_schema()
        # Add stable schema metadata that pydantic does not emit by default.
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"https://decisiontrace.org/reconstructor/v0.1.0/schemas/{filename}"
        path = args.out / filename
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
