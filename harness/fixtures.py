"""Fixtures: every model output, saved as it lands, under fixtures/<condition>/run-<k>.jsonl.

Record once, score many times. Nothing in here calls the model.

A file holds one JSON object per record, pretty-printed and appended as each call lands, so
it can be read by eye as well as by code. read() accepts that and the one-line-per-record
form alike. The policy the outputs were recorded with is kept in fixtures/policy.txt, and
the judge is shown that copy.
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path("fixtures")
POLICY_FILE = FIXTURES / "policy.txt"


def policy() -> str:
    """The policy text the fixtures were recorded with."""
    if not POLICY_FILE.exists():
        raise SystemExit(f"no {POLICY_FILE}: nothing has been recorded yet")
    return POLICY_FILE.read_text()


def save_policy(policy_text: str) -> None:
    """Keep the policy next to the recordings. Refuse to mix two policies in one set of fixtures."""
    recorded = any(FIXTURES.glob("*/run-*.jsonl"))
    if POLICY_FILE.exists() and POLICY_FILE.read_text() != policy_text and recorded:
        raise SystemExit(f"the policy in system/triage.py differs from {POLICY_FILE}, and fixtures/ already "
                         f"has recordings made with that one. Restore the policy, or move the old fixtures away.")
    FIXTURES.mkdir(parents=True, exist_ok=True)
    POLICY_FILE.write_text(policy_text)


def run_path(condition: str, run: int) -> Path:
    return FIXTURES / condition / f"run-{run}.jsonl"


def judge_path(condition: str, run_name: str) -> Path:
    """The judge's verdicts for one run: fixtures/<condition>/judge-<run>.jsonl."""
    return FIXTURES / condition / f"judge-{run_name}.jsonl"


def read(path: Path) -> list[dict]:
    """Every record in a fixture file: JSON objects one after another, however they are laid out."""
    if not path.exists():
        return []
    text, pos, records, decoder = path.read_text(), 0, [], json.JSONDecoder()
    while (pos := len(text) - len(text[pos:].lstrip())) < len(text):
        record, pos = decoder.raw_decode(text, pos)
        records.append(record)
    return records


def recorded_ids(path: Path) -> set[str]:
    """Which tickets this run file already holds, so a rerun continues rather than repeats."""
    return {r["id"] for r in read(path)}


def append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record, indent=2, ensure_ascii=False) + "\n")


def runs(condition: str) -> list[tuple[str, list[dict]]]:
    """(run name, records) for every run recorded under a condition, in order.

    If the judge has been run on it, each record also carries its verdicts under "judge".
    """
    out = []
    for path in sorted((FIXTURES / condition).glob("run-*.jsonl")):
        records = read(path)
        jpath = judge_path(condition, path.stem)
        if jpath.exists():
            verdicts = {j["id"]: j for j in read(jpath)}
            for r in records:
                if r["id"] in verdicts:
                    r["judge"] = {k: v for k, v in verdicts[r["id"]].items()
                                  if k not in ("id", "run", "condition", "version")}
        out.append((path.stem, records))
    return out
