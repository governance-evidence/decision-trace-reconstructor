"""Disclosed structural recovery; never edits a model's labels or evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from copy import deepcopy
from pathlib import Path

from experiments.paper23.client import load_key
from experiments.paper23.storage import digest, read, write
from experiments.paper23_assessor_v2.client import transport
from experiments.paper23_assessor_v2.rubric import admissibility, validate
from experiments.paper23_assessor_v2.runner import run_controls, run_main, sha
from experiments.paper23_assessor_v2_transport_r4 import CompatibleClient


def unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = item
    return value


def extract(text):
    """Require one outer complete JSON object; preserve its exact UTF-8 slice."""
    decoder = json.JSONDecoder(object_pairs_hook=unique_pairs)
    candidates = []
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, end = decoder.raw_decode(text, start)
        except ValueError:
            continue
        if isinstance(value, dict):
            candidates.append((start, end, value))
    outer = [c for c in candidates if not any(p[0] < c[0] and p[1] >= c[1] for p in candidates)]
    if len(outer) != 1 or set(outer[0][2]) != {"questions"}:
        raise ValueError(
            "No unique complete questions JSON object; ambiguous, duplicated or truncated content"
        )
    start, end, value = outer[0]
    # A truncated outer object may contain a complete nested questions object.
    # Any unmatched braces outside the accepted object make extraction unsafe.
    outside = text[:start] + text[end:]
    if "{" in outside or "}" in outside:
        raise ValueError("Unmatched or additional JSON-like object outside response")
    raw = text[start:end]
    proof = {
        "utf8_start": len(text[:start].encode()),
        "utf8_end": len(text[:end].encode()),
        "slice_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "exact_json_slice": raw,
        "parsed": value,
        "parsed_sha256": digest(value),
    }
    return value, proof


def check_amendment(root):
    if read(root / "normalization-amendment.json")["extension_sha256"] != sha(__file__):
        raise ValueError("Frozen lexical normalizer changed")


def recover_controls(root):
    check_amendment(root)
    source = Path(read(root / "normalization-amendment.json")["predecessor"])
    if not (source / "control-gate.json").exists():
        raise ValueError("Preserve completed predecessor gate before recovery")
    source_files = read(root / "normalization-amendment.json")["predecessor_files"]
    if any(sha(source / p) != h for p, h in source_files.items()):
        raise ValueError("Predecessor changed")
    results = []
    for case in read(root / "control-expectations.json"):
        packet_id = case["packet_id"]
        path = source / "assessments/controls" / (packet_id + ".json")
        original = read(path)
        target = root / "assessments/controls" / (packet_id + ".json")
        if target.exists():
            raise ValueError("Recovered control already exists")
        audit = deepcopy(original)
        packet = read(root / "packets/controls" / (packet_id + ".json"))
        try:
            value, proof = extract(original["responses"][-1]["content"])
            validate(value, packet)
        except (ValueError, TypeError, KeyError) as exc:
            audit.update(status="invalid_assessment", structural_recovery_error=str(exc))
        else:
            audit.update(
                status="complete",
                assessment=value,
                admissibility_flags=admissibility(value, packet),
                structural_recovery={
                    "source": str(path),
                    "source_sha256": sha(path),
                    "source_status": original["status"],
                    "last_response_request_id": original["responses"][-1]["request_id"],
                    "proof": proof,
                    "recovered": time.time(),
                    "new_api_calls": 0,
                },
            )
        write(target, audit)
        results.append({"packet_id": packet_id, "status": audit["status"]})
    return results


class NormalizingClient(CompatibleClient):
    def __init__(self, root, key, send=transport):
        root = Path(root)
        check_amendment(root)

        def normalized(secret, payload):
            response = send(secret, payload)
            request_id = read(root / "budget.json")["requests"][-1]["id"]
            write(root / "raw-responses" / (request_id + ".json"), response)
            if response.get("error") or not response.get("choices"):
                return response
            content = response["choices"][0]["message"].get("content") or ""
            try:
                value, proof = extract(content)
            except ValueError as exc:
                write(
                    root / "normalization" / (request_id + ".json"),
                    {"accepted": False, "error": str(exc)},
                )
                return response
            write(root / "normalization" / (request_id + ".json"), {"accepted": True, **proof})
            copy = deepcopy(response)
            copy["choices"][0]["message"]["content"] = json.dumps(value, ensure_ascii=False)
            return copy

        super().__init__(root, key, send=normalized)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("command", choices=["recover-controls", "main"])
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    root = args.study.resolve()
    if args.command == "recover-controls":
        recover_controls(root)

        class NoCalls:
            def complete(self, *args):
                raise AssertionError("Control recovery cannot make model calls")

        result = run_controls(root, NoCalls())
    else:
        result = run_main(root, NormalizingClient(root, load_key(args.env_file)))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
