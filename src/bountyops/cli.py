from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import RunRequest
from .orchestrator import run_bountyops


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BountyOps locally.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("input", type=Path)
    run_cmd.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.cmd == "run":
        payload = json.loads(args.input.read_text())
        request = RunRequest(**payload)
        result = run_bountyops(request)
        encoded = json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False)
        if args.out:
            args.out.write_text(encoded)
            print(f"Wrote {args.out}")
        else:
            print(encoded)


if __name__ == "__main__":
    main()
