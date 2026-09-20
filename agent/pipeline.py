"""Stage 1 spine: text in -> classification, forum, draft, trace."""
from datetime import date

from agent import classify as clf, client, draft as drafter, forum as forum_mod


def _step(trace: list, name: str) -> None:
    t = client.last_trace()
    trace.append({"step": name, "model": t.get("model", ""), "ms": t.get("ms", 0),
                  "cached": bool(t.get("cached"))})


def run_intake(text: str, module_override: str | None = None, answers: str | None = None) -> dict:
    today = date.today().isoformat()
    if answers:
        text = f"{text}\nAnswer: {answers}"

    trace: list = []
    classification = clf.classify(text, today=today)
    _step(trace, "classify")

    module = module_override or classification["module"]
    classification["module"] = module

    result = {"classification": classification, "forum": None, "draft": None, "trace": trace,
              "sections_dropped": [], "missing_fact": classification.get("missing_fact")}

    # One question, once: if the classifier wants a fact and nobody answered yet, stop and ask.
    if result["missing_fact"] and not answers:
        return result

    if module != "consumer":
        # stage2: police and tenant branches hook in here (same shape: forum/draft/sections_dropped).
        return result

    facts = classification["facts"]
    result["forum"] = forum_mod.compute(facts.get("amount_inr"))
    draft = drafter.draft_consumer(facts, result["forum"], today=today)
    _step(trace, "draft_consumer")
    result["draft"] = draft
    result["sections_dropped"] = draft.get("sections_dropped", [])
    return result
