"""V3 semantics with explicit, non-mutating output consistency checks."""

from experiments.paper23_assessor_v3.rubric import (
    OBLIGATIONS,
    STATUSES,
)
from experiments.paper23_assessor_v3.rubric import (
    PROMPT as V3_PROMPT,
)
from experiments.paper23_assessor_v3.rubric import (
    admissibility as admissibility,
)
from experiments.paper23_assessor_v3.rubric import (
    derive as derive,
)
from experiments.paper23_assessor_v3.rubric import (
    model_view as model_view,
)
from experiments.paper23_assessor_v3.rubric import (
    schema as v3_schema,
)
from experiments.paper23_assessor_v3.rubric import (
    validate as v3_validate,
)

PROMPT = (
    V3_PROMPT
    + """

OUTPUT CONTRACT: Return one complete JSON object, with Q1 through Q7, and no surrounding prose. Every evidence list and every contradictions list contains ONLY exact record IDs copied from this packet, never explanatory sentences. Put explanations in answer/reason. If a status is missing, its evidence list MUST be []. Do not place related/background records in that missing slot. If a status is supported or partial, cite at least one record. If a status is contradictory, cite at least two conflicting records in that obligation's evidence slot AND in the question's contradictions list. If no status in a question is contradictory, contradictions MUST be []. Conflicting IDs must come from that question's contradictory evidence slots. Lists contain distinct IDs, at most six. These are encoding constraints; do not change an evidence judgement to evade them.
Before returning JSON, check every missing slot is empty and every list item is an exact packet ID. Do not return a discussion of the schema. On a correction request, return the whole corrected JSON object, preserving all previously assigned obligation statuses.
"""
)


def schema():
    result = v3_schema()
    for item in result["properties"]["questions"]["properties"].values():
        for ids in [
            *item["properties"]["evidence"]["properties"].values(),
            item["properties"]["contradictions"],
        ]:
            ids["uniqueItems"] = True
            ids["description"] = (
                "Exact packet record IDs only. No prose. Missing slots must be empty."
            )
        item["properties"]["contradictions"]["description"] = (
            "Exact IDs of conflicting records cited in contradictory obligation slots; empty if none."
        )
    return result


def status_snapshot(value):
    result = {}
    questions = value.get("questions") if isinstance(value, dict) else None
    if not isinstance(questions, dict):
        return result
    for q, slots in OBLIGATIONS.items():
        item = questions.get(q)
        statuses = item.get("statuses") if isinstance(item, dict) else None
        if isinstance(statuses, dict):
            for slot in slots:
                status = statuses.get(slot)
                if isinstance(status, str) and status in STATUSES:
                    result[q + "." + slot] = status
    return result


def validate(value, packet, locked_statuses=None):
    if not isinstance(value, dict) or not isinstance(value.get("questions"), dict):
        raise ValueError("Return a complete object with a questions object Q1 through Q7")
    v3_validate(value, packet)
    current = status_snapshot(value)
    if locked_statuses and any(current.get(k) != v for k, v in locked_statuses.items()):
        raise ValueError(
            "Correction changed a locked obligation status; semantic revision prohibited"
        )
    for q, item in value["questions"].items():
        for ids in [*item["evidence"].values(), item["contradictions"]]:
            if len(ids) != len(set(ids)):
                raise ValueError(q + ": use distinct record IDs in each list")
        conflicting = set()
        for slot, status in item["statuses"].items():
            ids = item["evidence"][slot]
            if status == "missing" and ids:
                raise ValueError(
                    q
                    + "."
                    + slot
                    + ": missing status requires an empty evidence list; preserve status"
                )
            if status in ("supported", "partial", "not_required") and not ids:
                raise ValueError(
                    q + "." + slot + ": this status requires record IDs; preserve status"
                )
            if status == "contradictory":
                if len(ids) < 2:
                    raise ValueError(
                        q
                        + "."
                        + slot
                        + ": contradictory requires at least two distinct record IDs; preserve status"
                    )
                conflicting.update(ids)
        if conflicting:
            if len(item["contradictions"]) < 2 or not set(item["contradictions"]) <= conflicting:
                raise ValueError(
                    q + ": contradictions must cite at least two exact IDs from contradictory slots"
                )
        elif item["contradictions"]:
            raise ValueError(
                q
                + ": no contradictory status means contradictions must be empty; preserve statuses"
            )
    return value
