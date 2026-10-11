"""Paper23 V4 frozen output-contract calibration and reassessment."""

import argparse
import json
from pathlib import Path

from experiments.paper23.client import load_key

from .client import Client
from .lifecycle import freeze, prepare, verify_preservation
from .runner import run_controls, run_main, verify_control_gate
from .scoring import compare, score


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument(
        "command",
        choices=["prepare", "freeze", "controls", "main", "score", "compare", "verify", "gate"],
    )
    p.add_argument("--study", type=Path, required=True)
    p.add_argument("--predecessor", type=Path)
    p.add_argument("--protocol", type=Path)
    p.add_argument("--env-file", type=Path)
    a = p.parse_args()
    root = a.study.resolve()
    if a.command == "prepare":
        result = prepare(root, a.predecessor.resolve(), a.protocol.resolve(), load_key(a.env_file))
    elif a.command == "freeze":
        result = freeze(root)
    elif a.command in ("controls", "main"):
        client = Client(root, load_key(a.env_file))
        result = (run_controls if a.command == "controls" else run_main)(root, client)
    else:
        result = {
            "score": score,
            "compare": compare,
            "verify": verify_preservation,
            "gate": verify_control_gate,
        }[a.command](root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
