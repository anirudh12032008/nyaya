"""Stage 1: Haiku classifier. Text in (hi/hinglish/en) -> facts dict."""
from datetime import date

from agent import client, prompts

EMPTY_FACTS = {"parties": [], "amount_inr": None, "date_of_cause": None, "what_happened": ""}


def classify(text: str, today: str | None = None) -> dict:
    today = today or date.today().isoformat()
    raw = client.ask(
        client.HAIKU,
        prompts.load("classify"),
        f"Today's date is {today}.\n\nClient said:\n{text}",
        json_mode=True,
        temperature=0,
    )
    out = raw if isinstance(raw, dict) else {}
    facts = {**EMPTY_FACTS, **(out.get("facts") or {})}
    try:
        facts["amount_inr"] = int(facts["amount_inr"]) if facts["amount_inr"] is not None else None
    except (TypeError, ValueError):
        facts["amount_inr"] = None
    return {
        "module": out.get("module") or "other",
        "jurisdiction": out.get("jurisdiction") or "Madhya Pradesh",
        "urgency": out.get("urgency") or "medium",
        "language": out.get("language") or "en",
        "facts": facts,
        "missing_fact": out.get("missing_fact") or None,
    }
