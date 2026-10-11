"""Commands for the separately preserved assessor-v2 study."""

import argparse
import json
from pathlib import Path

from experiments.paper23.client import load_key

from .client import Client
from .runner import freeze, prepare, run_controls, run_main, verify_original
from .scoring import compare, score


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "command", choices=["prepare", "freeze", "controls", "main", "score", "compare", "verify"]
    )
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--original", type=Path)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    root = args.study.resolve()
    if args.command == "prepare":
        result = prepare(root, args.original, args.protocol)
    elif args.command == "freeze":
        result = freeze(root)
    elif args.command in ("controls", "main"):
        client = Client(root, load_key(args.env_file))
        result = (run_controls if args.command == "controls" else run_main)(root, client)
    elif args.command == "score":
        result = score(root)
    elif args.command == "compare":
        result = compare(root)
    else:
        result = verify_original(root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
