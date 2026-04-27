"""Stage 5: decision-event schema mapping.

Projects reconstructed decision units onto decision-event properties and assigns
a feasibility category to each property based on which fragments cover which
property and the scenario's architecture/stack profile.
"""

from __future__ import annotations

from .aggregation import map_chain_to_schema_aggregate
from .classification import map_chain_to_schema, map_unit_to_schema
from .modes import unrecoverable_mode_for_property

__all__ = [
    "map_chain_to_schema",
    "map_chain_to_schema_aggregate",
    "map_unit_to_schema",
    "unrecoverable_mode_for_property",
]
