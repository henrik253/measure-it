"""Record: run the system under test over the golden set and keep every call.

    uv run record.py --runs 5                          # policy beside the ticket  -> fixtures/policy-in-user/
    uv run record.py --runs 5 --policy-in system       # policy as the system instruction -> fixtures/policy-in-system/
    uv run record.py --runs 1 --provider fake          # no key, NOT a model -> fixtures/fake/
    uv run record.py --runs 5 --limit 3                # three tickets, to test
    uv run record.py --name my-prompt-edit --runs 5    # any other condition you make: name it yourself

The condition name is the folder under fixtures/. It defaults to what the flags say.
The policy in system/triage.py is saved next to the recordings as fixtures/policy.txt.
Writes fixtures/<condition>/run-<k>.jsonl, one pretty-printed JSON object per call, as each call lands. Resumable:
a call already in the file is never made again, so after a rate limit or the daily cap,
rerun the same command and it continues where it stopped.
"""
from __future__ import annotations

import argparse

from harness import fixtures, golden
from system import DEFAULT_MODEL, POLICY, triage


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", help="the condition being recorded; default: policy-in-<user|system>, or fake")
    p.add_argument("--runs", type=int, default=1, help="passes over the whole suite")
    p.add_argument("--policy-in", choices=["user", "system"], default="user")
    p.add_argument("--provider", choices=["gemini", "fake"], default="gemini")
    p.add_argument("--limit", type=int, help="only the first N tickets")
    args = p.parse_args()
    name = args.name or ("fake" if args.provider == "fake" else f"policy-in-{args.policy_in}")

    items = golden.load_golden()[: args.limit]
    accounts = golden.load_accounts()
    fixtures.save_policy(POLICY)
    for run in range(1, args.runs + 1):
        path = fixtures.run_path(name, run)
        done = fixtures.recorded_ids(path)
        todo = [i for i in items if i["id"] not in done]
        print(f"{name} run {run}: {len(done)} recorded, {len(todo)} to go "
              f"({DEFAULT_MODEL} via {args.provider}, policy in the {args.policy_in} text)", flush=True)
        for item in todo:
            rec = triage(item["ticket"], accounts[item["account"]],
                         provider=args.provider, policy_in=args.policy_in)
            rec.update({"id": item["id"], "run": run, "condition": name})
            fixtures.append(path, rec)
            print(f"  {item['id']}  {rec['action']:9s} {'' if rec['refund_amount'] is None else rec['refund_amount']}", flush=True)


if __name__ == "__main__":
    main()
