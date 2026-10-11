"""Fixed alternative provider with separate durable aggregate budget ledger."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from experiments.paper23.client import BASE
from experiments.paper23.storage import Budget, write

from .rubric import schema

MODEL = "anthropic/claude-sonnet-4.6"
PROVIDER = {
    "only": ["anthropic"],
    "order": ["anthropic"],
    "allow_fallbacks": False,
    "require_parameters": True,
    "max_price": {"prompt": 3, "completion": 15, "request": 0},
}
MAX_TOKENS = 3000


def transport(key, payload):
    request = urllib.request.Request(
        BASE + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "X-Title": "Paper23 assessor v3",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode().replace(key, "[REDACTED]"))


class Client:
    def __init__(self, root, key, send=transport):
        self.root = Path(root)
        if not (self.root / "budget.json").exists():
            raise ValueError("Prepare the carried-forward aggregate budget before calls")
        self.key = key
        self.send = send
        self.budget = Budget(root)

    def complete(self, run_id, messages):
        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0,
            "reasoning": {"enabled": False},
            "max_tokens": MAX_TOKENS,
            "provider": PROVIDER,
            "stream": False,
        }
        payload["messages"] = [dict(m) for m in messages]
        payload["messages"][0]["content"] += (
            "\n\nOutput-format schema (format only; no evidence or target labels):\n"
            + json.dumps(schema(), separators=(",", ":"))
        )
        upper_input = len(json.dumps(payload, ensure_ascii=False).encode()) + 4096
        bound = upper_input * 3 / 1e6 + MAX_TOKENS * 15 / 1e6
        for attempt in range(2):
            request_id = self.budget.reserve(run_id, bound, upper_input)
            target = self.root / "transport" / (request_id + ".json")
            row = {
                "run_id": run_id,
                "request_id": request_id,
                "attempt": attempt,
                "request": payload,
                "started": time.time(),
                "input_bound": upper_input,
            }
            write(target, row)
            try:
                response = self.send(self.key, payload)
            except (urllib.error.URLError, TimeoutError) as exc:
                code = getattr(exc, "code", None)
                row.update(error_type=type(exc).__name__, http_status=code, ended=time.time())
                if isinstance(exc, urllib.error.HTTPError):
                    body = exc.read().decode(errors="replace").replace(self.key, "[REDACTED]")
                    try:
                        error = json.loads(body).get("error", {})
                        row["provider_error"] = {
                            k: error[k] for k in ("code", "message") if k in error
                        }
                    except (ValueError, AttributeError):
                        row["provider_error"] = {"message": "Unparseable provider error"}
                write(target, row)
                self.budget.settle(
                    request_id, {}, {"http_status": code, "input_bound": upper_input}
                )
                if attempt == 1 or code is not None and code not in {408, 429, 500, 502, 503, 504}:
                    raise RuntimeError(
                        f"Provider request failed, HTTP {code}; reservation retained"
                    ) from None
                time.sleep(1)
                continue
            row.update(response=response, ended=time.time())
            write(target, row)
            self.budget.settle(
                request_id,
                response.get("usage", {}),
                {
                    "generation_id": response.get("id"),
                    "provider": response.get("provider"),
                    "model": response.get("model"),
                    "elapsed_s": row["ended"] - row["started"],
                },
            )
            if (
                response.get("error")
                or response.get("provider", "").lower() != "anthropic"
                or not response.get("model", "").startswith(MODEL)
            ):
                raise RuntimeError(
                    "Response error or provider/model route mismatch; inspect retained transport"
                )
            return response, request_id
        raise AssertionError("Unreachable")
