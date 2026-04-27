"""JSON-LD context and namespace constants for PROV-O output."""

from __future__ import annotations

from typing import Any

PROV_NS = "http://www.w3.org/ns/prov#"

DEMM_NS = "https://decisiontrace.org/demm/v1#"

SCHEMA_NS = "https://decisiontrace.org/schema/v1#"

CONTEXT: dict[str, Any] = {
    "prov": PROV_NS,
    "demm": DEMM_NS,
    "schema": SCHEMA_NS,
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "DecisionChain": "demm:DecisionChain",
    "DecisionUnit": "demm:DecisionUnit",
    "Fragment": "demm:Fragment",
    "PropertyFeasibility": "demm:PropertyFeasibility",
    "perPropertyFeasibility": {
        "@id": "demm:perPropertyFeasibility",
        "@container": "@set",
    },
    "members": {
        "@id": "prov:hadMember",
        "@container": "@set",
        "@type": "@id",
    },
    "fragments": {
        "@id": "prov:wasInfluencedBy",
        "@container": "@set",
        "@type": "@id",
    },
    "property": {"@id": "demm:property", "@type": "@id"},
    "category": {"@id": "demm:category"},
    "gap": {"@id": "demm:gap"},
    "completeness": {
        "@id": "demm:completeness",
        "@type": "xsd:decimal",
    },
    "completenessPct": {
        "@id": "demm:completenessPct",
        "@type": "xsd:decimal",
    },
    "dominantMode": {
        "@id": "demm:dominantMode",
        "@type": "xsd:integer",
    },
    "dominantBreak": {"@id": "demm:dominantBreak"},
    "architecture": {"@id": "demm:architecture"},
    "stackTier": {"@id": "demm:stackTier"},
    "actorId": {"@id": "demm:actorId"},
    "fragmentKind": {"@id": "demm:fragmentKind"},
    "boundaryReason": {"@id": "demm:boundaryReason"},
    "boundaryConfidence": {
        "@id": "demm:boundaryConfidence",
        "@type": "xsd:decimal",
    },
}


__all__ = ["CONTEXT", "DEMM_NS", "PROV_NS", "SCHEMA_NS"]
