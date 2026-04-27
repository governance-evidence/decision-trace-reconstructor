"""Stable IRI and timestamp helpers for PROV-O JSON-LD output."""

from __future__ import annotations

from datetime import UTC, datetime

from ..core.chain import DecisionUnit
from ..core.fragment import Fragment


def _ts(epoch_seconds: float) -> str:
    """Render a Unix-epoch timestamp as an ISO 8601 string in UTC."""
    return datetime.fromtimestamp(epoch_seconds, tz=UTC).isoformat()


def _frag_iri(scenario_id: str, frag: Fragment) -> str:
    return f"trace:{scenario_id}#frag/{frag.fragment_id}"


def _unit_iri(scenario_id: str, unit: DecisionUnit) -> str:
    return f"trace:{scenario_id}#unit/{unit.unit_id}"


def _agent_iri(scenario_id: str, actor_id: str) -> str:
    return f"trace:{scenario_id}#agent/{actor_id}"


def _chain_iri(scenario_id: str) -> str:
    return f"trace:{scenario_id}"


def _property_iri(prop_name: str) -> str:
    return f"schema:{prop_name}"
