"""Run the judge several more times on the 30 validation outputs, to measure its own noise.

    uv run python -m validation.rejudge     # 3 repeats (about 90 calls)
    uv run python -m validation.rejudge --repeats 1

Reads validation/judge-labels.json, writes validation/judge-repeats.json: per output, one verdict
set per repeat. Resumable: a repeat already saved is not made again.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from harness import fixtures, golden
from harness.judge import judge

HERE = Path(__file__).parent
LABELS, OUT = HERE / "judge-labels.json", HERE / "judge-repeats.json"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--provider", choices=["gemini", "fake"], default="gemini")
    args = p.parse_args()

    outputs = json.loads(LABELS.read_text())["outputs"]
    items = {i["id"]: i for i in golden.load_golden()}
    policy = fixtures.policy()
    saved = json.loads(OUT.read_text()) if OUT.exists() else {}
    for o in outputs:
        key = f"{o['condition']}/run-{o['run']}/{o['id']}"
        rec = next(r for name, rs in fixtures.runs(o["condition"]) if name == f"run-{o['run']}"
                   for r in rs if r["id"] == o["id"])
        repeats = saved.setdefault(key, [])
        while len(repeats) < args.repeats:
            repeats.append(judge(items[o["id"]], rec, provider=args.provider, policy=policy))
            OUT.write_text(json.dumps(saved, indent=2) + "\n")
            print(f"{key}  repeat {len(repeats)}: " + "  ".join(f"{k}={'yes' if v else 'no'}" for k, v in repeats[-1].items()), flush=True)


if __name__ == "__main__":
    main()
