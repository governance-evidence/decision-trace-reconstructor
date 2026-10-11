"""Packet assessment and scoring commands; never generate human approvals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.paper23.client import Client, load_key

from .judge import assess
from .scoring import freeze_analysis, pin_instrument, score


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("command", choices=["judge", "pin", "freeze-analysis", "score"])
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--phase", choices=["pilot", "main"], default="pilot")
    parser.add_argument("--pass-name", choices=["reduced", "full"], default="reduced")
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    if args.command == "judge":
        result = assess(
            args.study, args.phase, args.pass_name, Client(args.study, load_key(args.env_file))
        )
    elif args.command == "pin":
        result = {"instrument": str(pin_instrument(args.study))}
    elif args.command == "freeze-analysis":
        result = freeze_analysis(args.study)
    else:
        result = score(args.study, args.phase)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
