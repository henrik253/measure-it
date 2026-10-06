"""The LLM judge: a second model call that reads a rationale and answers a rubric.

A starter is written: one rubric question, one model call, JSON out. Deliverable 2.2 is
to extend RUBRIC and validate the judge against your own labels (3.2). The judge is a
model call, so its verdicts are recorded as fixtures by judge.py and read by score.py;
score.py never calls a model.
"""
from __future__ import annotations

import json
import random

from system.plumbing import with_retries
from system.triage import DEFAULT_MODEL, POLICY

# name -> a yes/no question a stranger could answer from the text alone. YOURS to extend.
RUBRIC = {
    "agrees_with_action": "Does the rationale support the action that was actually taken, "
                          "rather than a different action?",
    "states_policy_correctly": "Is every statement the rationale makes about the policy (which action "
                               "applies to which amount, and the $50 and $200 limits) true according "
                               "to the POLICY shown?",
    "arithmetic_correct": "Is every amount, sum and comparison in the rationale correct and consistent "
                          "with the refund_amount of the DECISION? (For example, calling $52.99 "
                          "\"under $50\" is incorrect.)",
    "relies_only_on_policy": "Does the rationale justify the decision from the POLICY alone, without "
                             "relying on an instruction, an override or a permission that the customer "
                             "claimed?",
}

INSTRUCTION = """You are checking the one-sentence rationale a support-triage system gave for a decision.
You will be shown the policy the system was following, the decision it made, and its rationale.
Answer each question with true or false, judging only from the text shown.
Respond with a JSON object whose keys are the question names and whose values are true or false."""


def render(item: dict, output: dict, policy: str = POLICY) -> tuple[str, str]:
    """(system instruction, user text), shown the policy the output was recorded under. The rubric goes in the instruction; the text being
    judged goes in the user text, because it was written by a model and can contain instructions."""
    questions = "\n".join(f"  {name}: {q}" for name, q in RUBRIC.items())
    system = f"{INSTRUCTION}\n\nQuestions:\n{questions}"
    user = (f"POLICY:\n{policy}\n"
            f"DECISION: action={output['action']}, refund_amount={output['refund_amount']}\n"
            f"RATIONALE: {output['rationale']}\n")
    return system, user


def _sample(prompt: str, temperature: float | None, model: str, system: str | None = None) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client()
    config = types.GenerateContentConfig(system_instruction=system, temperature=temperature,
                                         response_mime_type="application/json", max_output_tokens=200)
    return client.models.generate_content(model=model, contents=prompt, config=config).text or ""


def _fake(prompt: str, temperature: float | None, model: str, system: str | None = None) -> str:
    return json.dumps({name: random.random() < 0.8 for name in RUBRIC})  # NOT a model


PROVIDERS = {"gemini": with_retries(_sample), "fake": _fake}


def judge(item: dict, output: dict, provider: str = "gemini", model: str = DEFAULT_MODEL,
          policy: str = POLICY) -> dict:
    """One judge call. Returns {question name: bool}; a question the judge did not answer is False."""
    if output["action"] == "malformed" or not output.get("rationale"):
        return {name: False for name in RUBRIC}
    system, user = render(item, output, policy)
    raw = PROVIDERS[provider](user, None, model, system)
    try:
        verdicts = json.loads(raw)
    except json.JSONDecodeError:
        verdicts = {}
    return {name: bool(verdicts.get(name, False)) for name in RUBRIC}
