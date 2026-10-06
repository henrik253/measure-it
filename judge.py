"""Judge: run the LLM judge over recorded outputs and save its verdicts as fixtures.

    uv run judge.py policy-in-user                 # every run under fixtures/policy-in-user
    uv run judge.py policy-in-user policy-in-system  # several conditions
    uv run judge.py policy-in-user --provider fake # no key, NOT a model

The judge is shown the policy the outputs were recorded with (fixtures/policy.txt).
Writes fixtures/<condition>/judge-<run>.jsonl, one pretty-printed JSON object per rationale. Like record.py it
is resumable and never repeats a verdict it already has. The rubric is in harness/judge.py.
"""
from __future__ import annotations

import argparse

from harness import fixtures, golden
from harness.judge import RUBRIC, judge


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("conditions", nargs="+")
    p.add_argument("--provider", choices=["gemini", "fake"], default="gemini")
    args = p.parse_args()

    items = {i["id"]: i for i in golden.load_golden()}
    policy = fixtures.policy()
    for condition in args.conditions:
        for run_name, records in fixtures.runs(condition):
            path = fixtures.judge_path(condition, run_name)
            done = fixtures.recorded_ids(path)
            todo = [r for r in records if r["id"] in items and r["id"] not in done]
            print(f"{condition} / {run_name}: {len(done)} judged, {len(todo)} to go ({len(RUBRIC)} question(s), via {args.provider})", flush=True)
            for rec in todo:
                verdicts = judge(items[rec["id"]], rec, provider=args.provider, policy=policy)
                fixtures.append(path, {"id": rec["id"], "run": rec["run"], "condition": condition, **verdicts})
                print(f"  {rec['id']}  " + "  ".join(f"{k}={'yes' if v else 'no'}" for k, v in verdicts.items()), flush=True)


if __name__ == "__main__":
    main()
