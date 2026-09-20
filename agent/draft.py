"""Stage 1: Sonnet drafts a consumer complaint. Money/forum/deadline stay in Python."""
import json
from datetime import date

from agent import client, prompts, sections as sec
from agent.data import load

DRAFT_KEYS = {"draft_markdown": "", "sections": [], "next_steps": [], "hindi_summary": "",
              "deadline_iso": None}


def _deadline(date_of_cause: str | None, years: int) -> str | None:
    if not date_of_cause:
        return None
    try:
        d = date.fromisoformat(str(date_of_cause)[:10])
    except ValueError:
        return None
    try:
        return d.replace(year=d.year + years).isoformat()
    except ValueError:  # 29 Feb
        return d.replace(year=d.year + years, day=28).isoformat()


def draft_consumer(facts: dict, forum: dict, today: str | None = None) -> dict:
    today = today or date.today().isoformat()
    portal = load("portals").get("consumer", {})
    slice_ = [{"id": s["id"], "title": s.get("title", ""), "gist": s.get("gist", "")}
              for s in sec.entries("consumer")]

    user = "\n\n".join([
        f"TODAY: {today}",
        "FACTS (JSON):\n" + json.dumps(facts, ensure_ascii=False, indent=1),
        "FORUM AND FEE, already computed in Python — copy verbatim:\n"
        + json.dumps(forum, ensure_ascii=False, indent=1),
        "SECTIONS YOU MAY CITE (no others):\n" + json.dumps(slice_, ensure_ascii=False, indent=1),
        "DOCUMENTS THE PORTAL REQUIRES:\n"
        + json.dumps(portal.get("documents", []), ensure_ascii=False)
        + f"\nPortal: {portal.get('portal_url', '')}",
    ])

    raw = client.ask(client.SONNET, prompts.load("draft_consumer"), user,
                     json_mode=True, temperature=0.3)
    out = {**DRAFT_KEYS, **(raw if isinstance(raw, dict) else {})}

    kept, dropped = sec.filter_sections("consumer", out.get("sections"))
    out["sections"], out["sections_dropped"] = kept, dropped

    computed = _deadline(facts.get("date_of_cause"), forum.get("limitation_years", 2))
    if computed:  # Python wins over whatever the model said
        out["deadline_iso"] = computed
    return out
