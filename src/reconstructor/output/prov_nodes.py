"""PROV-O JSON-LD node builders."""

from __future__ import annotations

from typing import Any

from ..core.chain import DecisionUnit
from ..core.fragment import Fragment
from ..mapping.feasibility import PropertyFeasibility
from ..pipeline import ReconstructionReport
from ..synthetic.generator import Scenario
from .prov_identifiers import (
    _agent_iri,
    _chain_iri,
    _frag_iri,
    _property_iri,
    _ts,
    _unit_iri,
)


def _fragment_node(scenario_id: str, frag: Fragment) -> dict[str, Any]:
    return {
        "@id": _frag_iri(scenario_id, frag),
        "@type": ["prov:Entity", "Fragment"],
        "prov:generatedAtTime": {
            "@value": _ts(frag.timestamp),
            "@type": "xsd:dateTime",
        },
        "prov:wasAttributedTo": {"@id": _agent_iri(scenario_id, frag.actor_id)},
        "fragmentKind": frag.kind.value,
        "demm:stackTier": frag.stack_tier.value,
    }


def _agent_node(scenario_id: str, actor_id: str) -> dict[str, Any]:
    return {
        "@id": _agent_iri(scenario_id, actor_id),
        "@type": "prov:Agent",
        "actorId": actor_id,
    }


def _unit_node(
    scenario_id: str,
    unit: DecisionUnit,
    feas_records: list[PropertyFeasibility] | None = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "@id": _unit_iri(scenario_id, unit),
        "@type": ["prov:Activity", "DecisionUnit"],
        "prov:startedAtTime": {
            "@value": _ts(unit.start_timestamp()),
            "@type": "xsd:dateTime",
        },
        "prov:endedAtTime": {
            "@value": _ts(unit.end_timestamp()),
            "@type": "xsd:dateTime",
        },
        "prov:wasAssociatedWith": {"@id": _agent_iri(scenario_id, unit.primary_actor())},
        "boundaryReason": unit.boundary_reason,
        "boundaryConfidence": unit.boundary_confidence,
        "fragments": [_frag_iri(scenario_id, f) for f in unit.fragments],
    }
    if feas_records:
        node["perPropertyFeasibility"] = [
            _feasibility_node(scenario_id, unit, f) for f in feas_records
        ]
    return node


def _feasibility_node(
    scenario_id: str,
    unit: DecisionUnit,
    feas: PropertyFeasibility,
) -> dict[str, Any]:
    return {
        "@id": (f"trace:{scenario_id}#unit/{unit.unit_id}/feas/{feas.property_name}"),
        "@type": "PropertyFeasibility",
        "property": _property_iri(feas.property_name),
        "category": feas.category.value,
        "gap": feas.gap_description,
        "demm:confidence": feas.confidence,
    }


def _chain_node(
    scenario: Scenario,
    report: ReconstructionReport,
    chain_feas: list[PropertyFeasibility],
) -> dict[str, Any]:
    sid = scenario.scenario_id
    dominant_mode = report.dominant_mode()
    dominant_break = report.dominant_break()
    return {
        "@id": _chain_iri(sid),
        "@type": ["prov:Collection", "DecisionChain"],
        "demm:scenarioId": sid,
        "architecture": scenario.architecture.value,
        "stackTier": scenario.stack_tier.value,
        "completeness": round(report.completeness, 4),
        "dominantMode": dominant_mode.value if dominant_mode else None,
        "dominantBreak": dominant_break.value if dominant_break else None,
        "members": [_unit_iri(sid, u) for u in report.chain.units],
        "perPropertyFeasibility": [
            {
                "@id": f"trace:{sid}#chain/feas/{f.property_name}",
                "@type": "PropertyFeasibility",
                "property": _property_iri(f.property_name),
                "category": f.category.value,
                "gap": f.gap_description,
                "demm:confidence": f.confidence,
            }
            for f in chain_feas
        ],
    }
