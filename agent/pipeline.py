"""Stage 1 spine: text in -> classification, forum, draft, trace."""
from datetime import date

from agent import classify as clf, client, draft as drafter, forum as forum_mod, verify as ver


def _step(trace: list, name: str) -> None:
    t = client.last_trace()
    trace.append({"step": name, "model": t.get("model", ""), "ms": t.get("ms", 0),
                  "cached": bool(t.get("cached"))})


def _verified(result: dict, module: str, facts: dict, text: str, today: str, trace: list) -> None:
    """Stage 5B: second-agent review; at most one redraft. Mutates result in place."""
    draft, forum = result["draft"], result["forum"]
    first = ver.verify(module, facts, forum, draft, raw_text=text, today=today)
    _step(trace, "verify")
    verification = {"pass": first["pass"], "issues": first["issues"], "redrafted": False,
                    "first_issues": first["issues"]}
    if first.get("skipped"):
        verification["skipped"] = first["skipped"]
    if first["pass"] is False:
        draft = ver.redraft_with_issues(module, facts, forum, draft, first["issues"], today,
                                        raw_text=text)
        _step(trace, "redraft")
        second = ver.verify(module, facts, forum, draft, raw_text=text, today=today)
        _step(trace, "verify_2")
        result["draft"], result["sections_dropped"] = draft, draft.get("sections_dropped", [])
        verification.update({"pass": second["pass"], "issues": second["issues"], "redrafted": True})
        if second.get("skipped"):
            verification["skipped"] = second["skipped"]
    result["verification"] = verification


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

    facts = classification["facts"]
    if module in ("police", "tenant"):  # stage2 branches, same result shape
        from agent import pipeline_modules
        draft = pipeline_modules.run_module(module, classification, text, today, trace)
        result["draft"] = draft
        result["sections_dropped"] = draft.get("sections_dropped", [])
        _verified(result, module, facts, text, today, trace)
        return result

    if module != "consumer":
        return result

    result["forum"] = forum_mod.compute(facts.get("amount_inr"))
    draft = drafter.draft_consumer(facts, result["forum"], today=today)
    _step(trace, "draft_consumer")
    result["draft"] = draft
    result["sections_dropped"] = draft.get("sections_dropped", [])
    _verified(result, module, facts, text, today, trace)
    return result
