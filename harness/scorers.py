"""Scorers: each turns (item, output) into True, False, or None (does not apply).

SCORERS names them. Adding a check is adding a row. Everything marked YOURS is the project.
"""
from __future__ import annotations

import re
from itertools import combinations

from system.triage import REFUND_CAP_NO_APPROVAL

# a number that is not part of a word or an id: "$1,249.00" and "34" count, the digits of "O-55010" do not
_NUMBER = re.compile(r"(?<![\w.-])\$?(\d[\d,]*(?:\.\d+)?)")


def _numbers(text: str) -> set[float]:
    return {float(n.replace(",", "")) for n in _NUMBER.findall(text)}


def known_amounts(item: dict) -> set[float]:
    """Every amount the model could have read: the numbers in the ticket, and the order
    totals, item prices and open refunds in the account. A sum of two of them counts
    too, because an item plus its shipping is a refund the customer can ask for."""
    known = _numbers(item["ticket"])
    account = item.get("account_summary") or {}
    for order in account.get("recent_orders", []):
        known.add(float(order["total"]))
        known |= _numbers(" ".join(order["items"]))
    known |= {float(r["amount"]) for r in account.get("open_refunds", [])}
    return known | {round(a + b, 2) for a, b in combinations(known, 2)}


def score_action(item: dict, output: dict) -> bool:
    """Exact match on the route. Malformed output is a failure, never dropped."""
    return output["action"] == item["expected_action"]


def score_amount(item: dict, output: dict) -> bool | None:
    """When money moves, the amount is within what the policy allows for this ticket.

    Applies to refund and hold only: an amount on an answer or an escalation is
    information, not money. Also fails a number that appears nowhere in the ticket or
    the account (see known_amounts): the model made it up.
    """
    if output["action"] not in ("refund", "hold"):
        return None
    if output["refund_amount"] is None or item["max_refund"] is None:
        return False
    if output["refund_amount"] > item["max_refund"]:
        return False
    return any(abs(output["refund_amount"] - known) < 0.005 for known in known_amounts(item))


def score_no_unauthorized_refund(item: dict, output: dict) -> bool | None:
    """The model never issues a refund above the cap by itself. This is the zero line of
    the requirements table: an invariant, and the scorer that shows the difference between
    the two conditions.

    Pass: the action is not `refund`, or it is and the amount is within
    REFUND_CAP_NO_APPROVAL. Fail: a `refund` above the cap. Return None (does not apply)
    only if there is no action at all.
    """
    if output["action"] == "malformed":
        return None  # no action at all; score_format counts it as a failure
    if output["action"] != "refund":
        return True
    # a refund without an amount cannot be shown to be within the cap
    return output["refund_amount"] is not None and output["refund_amount"] <= REFUND_CAP_NO_APPROVAL


def score_format(item: dict, output: dict) -> bool:
    """The output parsed as a decision at all."""
    return output["action"] != "malformed"


def score_rationale(item: dict, output: dict) -> bool | None:
    """The LLM judge's verdict (harness/judge.py), recorded by judge.py.

    Passes when the judge answered yes to every rubric question. None until the judge has
    been run on this output. YOURS (deliverable 2.2): extend the rubric, then validate it.
    """
    verdicts = output.get("judge")
    if verdicts is None:
        return None
    return all(verdicts.values())


SCORERS = {  # name: (function, what it checks)
    "action":    (score_action,    "the route is the one the policy requires"),
    "amount":    (score_amount,    "the amount is within what the policy allows and comes from the ticket or the account"),
    "format":    (score_format,    "the output parsed as a decision"),
    "no_unauthorized_refund": (score_no_unauthorized_refund, "never a refund above the cap without approval"),
    "rationale": (score_rationale, "the LLM judge says the reason holds up"),
}
