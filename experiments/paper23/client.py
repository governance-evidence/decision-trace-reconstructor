"""Fixed OpenRouter route with durable reservations and redacted transport records."""

from __future__ import annotations

import json
import os
import re
import shlex
import time
import urllib.error
import urllib.request
from pathlib import Path

from .storage import Budget, BudgetExceeded, read, write

MODEL = "openai/gpt-4.1-mini"
BASE = "https://openrouter.ai/api/v1"
PROVIDER = {
    "only": ["openai"],
    "order": ["openai"],
    "allow_fallbacks": False,
    "require_parameters": True,
    "max_price": {"prompt": 0.4, "completion": 1.6, "request": 0},
}


def load_key(env_file=None):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key and env_file:
        for line in Path(env_file).read_text().splitlines():
            match = re.match(r"\s*(?:export\s+)?OPENROUTER_API_KEY\s*=\s*(.*)", line)
            if match:
                pieces = shlex.split(match[1], comments=True)
                key = pieces[0] if len(pieces) == 1 else None
                break
    if not key or not key.startswith("sk-or-"):
        raise ValueError("A valid-looking OPENROUTER_API_KEY must be supplied locally")
    return key


def http_json(route, key, payload=None):
    request = urllib.request.Request(
        BASE + route,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "X-Title": "Paper23 controlled evaluation",
        },
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode().replace(key, "[REDACTED]"))


def probe(root, key):
    account = http_json("/key", key)["data"]
    model = next(m for m in http_json("/models", key)["data"] if m["id"] == MODEL)
    pricing = model["pricing"]
    if (
        float(pricing["prompt"]) > 0.4 / 1e6 + 1e-12
        or float(pricing["completion"]) > 1.6 / 1e6 + 1e-12
    ):
        raise ValueError("Current listed model prices exceed the protocol ceiling")
    snapshot = {
        "time": time.time(),
        "model": MODEL,
        "pricing": pricing,
        "supported_parameters": model.get("supported_parameters"),
        "credential_verified": True,
        "key_limit_remaining": account.get("limit_remaining"),
    }
    write(Path(root) / "provider-preflight.json", snapshot)
    return {"model": MODEL, "credential_verified": True, "pricing": pricing}


class Client:
    def __init__(self, root, key, transport=http_json):
        self.root, self.key, self.transport = Path(root), key, transport
        self.budget = Budget(root)

    def complete(self, run_id, messages, tools=None):
        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 1500,
            "provider": PROVIDER,
            "stream": False,
        }
        if tools:
            payload.update(tools=tools, tool_choice="auto")
        # UTF-8 byte count plus framing allowance is deliberately conservative.
        upper_input = len(json.dumps(payload, ensure_ascii=False).encode()) + 4096
        bound = upper_input * 0.4 / 1e6 + 1500 * 1.6 / 1e6
        for attempt in range(3):
            history = [r for r in read(self.budget.path)["requests"] if r["run_id"] == run_id]

            def tokens(row, field, fallback):
                value = row.get("usage", {}).get(field)
                return (
                    value
                    if isinstance(value, int) and not isinstance(value, bool) and value >= 0
                    else fallback
                )

            prior_input = sum(tokens(r, "prompt_tokens", r.get("input_bound", 0)) for r in history)
            prior_output = sum(tokens(r, "completion_tokens", 1500) for r in history)
            if prior_input + upper_input > 100000 or prior_output + 1500 > 20000:
                raise BudgetExceeded("Trajectory token cap would be exceeded")
            request_id = self.budget.reserve(run_id, bound, upper_input)
            target = self.root / "transport" / (request_id + ".json")
            record = {
                "run_id": run_id,
                "request_id": request_id,
                "attempt": attempt,
                "request": payload,
                "started": time.time(),
                "input_bound": upper_input,
            }
            write(target, record)
            try:
                response = self.transport("/chat/completions", self.key, payload)
            except (urllib.error.URLError, TimeoutError) as exc:
                code = getattr(exc, "code", None)
                record.update(error_type=type(exc).__name__, http_status=code, ended=time.time())
                if isinstance(exc, urllib.error.HTTPError):
                    body = exc.read().decode(errors="replace").replace(self.key, "[REDACTED]")
                    try:
                        error = json.loads(body).get("error", {})
                        record["provider_error"] = {
                            k: error[k] for k in ("code", "message") if k in error
                        }
                    except (ValueError, AttributeError):
                        record["provider_error"] = {"message": "Unparseable provider error body"}
                write(target, record)  # Never persist exception strings or request headers.
                self.budget.settle(
                    request_id, {}, {"input_bound": upper_input, "http_status": code}
                )
                if attempt == 2 or code is not None and code not in {408, 429, 500, 502, 503, 504}:
                    raise RuntimeError(
                        f"OpenRouter request failed ({type(exc).__name__}, HTTP {code}); reservation retained"
                    ) from None
                time.sleep(1 + attempt)
                continue
            record.update(response=response, ended=time.time())
            write(target, record)
            self.budget.settle(
                request_id,
                response.get("usage", {}),
                {
                    "input_bound": upper_input,
                    "generation_id": response.get("id"),
                    "provider": response.get("provider"),
                    "model": response.get("model"),
                    "elapsed_s": record["ended"] - record["started"],
                },
            )
            if "error" in response:
                raise RuntimeError("Provider returned an error body; see redacted transport record")
            if response.get("provider", "").lower() != "openai":
                raise RuntimeError("Returned provider differs from fixed OpenAI route")
            if not response.get("model", "").startswith("openai/gpt-4.1-mini"):
                raise RuntimeError("Returned model differs from the requested family")
            return response, request_id
        raise AssertionError("Unreachable")
