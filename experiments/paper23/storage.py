"""Durable study records and conservative, shared budget reservations."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)


@contextmanager
def locked(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def event(path, kind, actor, data, parent=None):
    record = {
        "id": uuid.uuid4().hex,
        "time": time.time(),
        "kind": kind,
        "actor": actor,
        "parent": parent,
        "data": data,
    }
    with Path(path).open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record["id"]


def events(path):
    return (
        [json.loads(line) for line in Path(path).read_text().splitlines()]
        if Path(path).exists()
        else []
    )


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, root, cap=5.0):
        self.root = Path(root)
        self.path = self.root / "budget.json"
        self.lock = self.root / "budget.lock"
        if not math.isfinite(cap) or not 0 < cap <= 5:
            raise ValueError("This study authorises a maximum USD 5 inference cap")
        with locked(self.lock):
            if not self.path.exists():
                write(self.path, {"cap_usd": cap, "requests": []})
            elif read(self.path)["cap_usd"] != cap:
                raise ValueError("An existing study's cap cannot be changed implicitly")

    def reserve(self, run_id, amount, input_bound=0):
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Reservation must be finite and positive")
        with locked(self.lock):
            data = read(self.path)
            if data.get("halted"):
                raise BudgetExceeded("Study halted after a billing-bound violation")
            used = sum(r["charged_or_reserved_usd"] for r in data["requests"])
            if used + amount > data["cap_usd"]:
                raise BudgetExceeded("Next request would exceed the study cap")
            request_id = uuid.uuid4().hex
            data["requests"].append(
                {
                    "id": request_id,
                    "run_id": run_id,
                    "reserved_usd": amount,
                    "charged_or_reserved_usd": amount,
                    "state": "reserved",
                    "time": time.time(),
                    "input_bound": input_bound,
                }
            )
            write(self.path, data)
            return request_id

    def settle(self, request_id, usage, metadata):
        with locked(self.lock):
            data = read(self.path)
            row = next(r for r in data["requests"] if r["id"] == request_id)
            row.update(metadata)
            row["usage"] = usage if isinstance(usage, dict) else {}
            cost = usage.get("cost") if isinstance(usage, dict) else None
            valid = (
                isinstance(cost, (float, int))
                and not isinstance(cost, bool)
                and math.isfinite(cost)
                and cost >= 0
            )
            row["state"] = "settled" if valid else "usage_unresolved"
            if valid:
                row["charged_or_reserved_usd"] = float(cost)
            if valid and cost > row["reserved_usd"]:
                data["halted"] = "charge_exceeded_reservation"
            write(self.path, data)
            if valid and cost > row["reserved_usd"]:
                raise BudgetExceeded(
                    "Provider charge exceeded reserved bound; stop for reconciliation"
                )

    def summary(self):
        data = read(self.path)
        return {
            "cap_usd": data["cap_usd"],
            "requests": len(data["requests"]),
            "reported_cost_usd": sum(
                r["charged_or_reserved_usd"] for r in data["requests"] if r["state"] == "settled"
            ),
            "reserved_or_charged_usd": sum(r["charged_or_reserved_usd"] for r in data["requests"]),
            "unresolved_requests": sum(r["state"] != "settled" for r in data["requests"]),
        }
