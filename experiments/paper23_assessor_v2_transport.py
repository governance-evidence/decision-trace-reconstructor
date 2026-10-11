"""Versioned wire-schema compatibility repair; frozen scientific code unchanged.

Anthropic rejects maxItems in structured-output schemas. Remove only this
wire constraint, retain the prompt and local six-ID validation, and record the
actual outgoing payload separately from the unchanged client's logical request.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
from copy import deepcopy
from pathlib import Path

from experiments.paper23.client import load_key
from experiments.paper23.storage import read, write
from experiments.paper23_assessor_v2.client import Client, transport
from experiments.paper23_assessor_v2.runner import run_controls, run_main, sha


def wire_payload(payload):
    value = deepcopy(payload)

    def visit(item):
        if isinstance(item, dict):
            item.pop("maxItems", None)
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value["response_format"]["json_schema"]["schema"])
    return value


class CompatibleClient(Client):
    def __init__(self, root, key, send=transport):
        root = Path(root)
        amendment = read(root / "transport-amendment.json")
        if amendment["extension_sha256"] != sha(__file__):
            raise ValueError("Frozen transport extension changed")

        def wrapped(secret, payload):
            # The study executes serially; the parent reserved/wrote this ID
            # immediately before entering the wire transport.
            request_id = read(root / "budget.json")["requests"][-1]["id"]
            logical = read(root / "transport" / (request_id + ".json"))
            if logical["request"] != payload:
                raise ValueError("Transport request/ledger identity mismatch")
            actual = wire_payload(payload)
            target = root / "wire-requests" / (request_id + ".json")
            wire = {
                "request_id": request_id,
                "request": actual,
                "change": "Removed only unsupported maxItems from wire JSON schema; prompt and local validation unchanged",
            }
            write(target, wire)
            try:
                return send(secret, actual)
            except urllib.error.HTTPError as exc:
                body = exc.read()
                try:
                    error = json.loads(body.decode().replace(secret, "[REDACTED]")).get("error", {})
                    wire["provider_diagnostic"] = {
                        "code": error.get("code"),
                        "message": error.get("message"),
                        "raw": error.get("metadata", {}).get("raw"),
                    }
                except (ValueError, AttributeError):
                    wire["provider_diagnostic"] = {"message": "Unparseable provider error"}
                write(target, wire)
                # Parent handler must still see the same error body.
                import io

                exc.fp = io.BytesIO(body)
                raise

        super().__init__(root, key, send=wrapped)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("command", choices=["controls", "main"])
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    root = args.study.resolve()
    client = CompatibleClient(root, load_key(args.env_file))
    result = (run_controls if args.command == "controls" else run_main)(root, client)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
