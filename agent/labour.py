"""Labour module: unpaid wages, illegal termination, PF/ESI non-deposit, gratuity (MP).

Mirrors agent/police.py. The grievance type is decided by keyword in Python, and
the forum, the limitation period and the deadline are then read out of
data/labour_rules.json — the model only writes prose over the slice it is handed.
"""
from __future__ import annotations

import json
import re
from datetime import date

from agent import client, prompts
from agent.data import load
from agent.sections import norm

# grievance key -> (keyword pattern, section ids to put in the slice).
# Order is the priority order: the first match decides the primary forum.
_TOPICS: list[tuple[str, str, list[str]]] = [
    ("unpaid_wages",
     r"unpaid|not paid|salary|salaries|wage|wages|tankhwah|tanakhwah|vetan|majdoori|"
     r"mazdoori|payroll|arrear|bakaya|pagar",
     ["PWA 15", "PWA 5"]),
    ("illegal_termination",
     r"terminat|fired|fire kar|dismiss|retrench|sack|removed|nikal diya|nikaal|hata diya|"
     r"naukri se|without notice|bina notice|bina soochna|layoff|laid off|chhant",
     ["ID Act 2A", "ID Act 25F", "ID Act 25B", "MP Shops 1958"]),
    ("gratuity",
     r"gratuity|graduity|upadan|उपदान",
     ["PGA 4", "PGA 7"]),
    ("pf_not_deposited",
     r"\bpf\b|provident|epf|uan|bhavishya nidhi|भविष्य निधि",
     ["EPF 7A", "EPF 14"]),
    ("esi_not_deposited",
     r"\besi\b|esic|state insurance|bima|बीमा",
     ["ESI 85"]),
    ("below_minimum_wage",
     r"minimum wage|nyuntam|न्यूनतम|below minimum|kam se kam majdoori",
     ["MWA 20"]),
]

# every labour draft sees the forum-defining sections whatever the grievance
ALWAYS = ["PWA 15", "MP Shops 1958", "Wages Code 45"]

_FALLBACK = "general"


def grievances(text: str, facts: dict | None = None) -> list[str]:
    """Keyword scan over the client's words plus the classifier's facts, in priority order."""
    blob = text or ""
    if facts:
        blob += " " + json.dumps(facts, ensure_ascii=False)
        if facts.get("months_unpaid"):
            blob += " unpaid wages"
        if facts.get("last_working_day"):
            blob += " terminated"
        if facts.get("pf_uan"):
            blob += " pf uan"
    hits = [key for key, pattern, _ in _TOPICS if re.search(pattern, blob, re.I)]
    return hits or [_FALLBACK]


def pick_forum(keys: list[str]) -> dict:
    """Primary forum for the first (highest priority) grievance; never model-chosen."""
    forums = load("labour_rules").get("forums", [])
    by_grievance = {f.get("grievance"): f for f in forums}
    for key in list(keys) + [_FALLBACK]:
        if key in by_grievance:
            return by_grievance[key]
    return forums[0] if forums else {}


def pick_limitation(keys: list[str]) -> dict:
    """Limitation entry for the first grievance we know a period for."""
    table = load("labour_rules").get("limitation", {})
    for key in list(keys) + [_FALLBACK]:
        if key in table:
            return {"grievance": key, **table[key]}
    return {}


def _add_months(iso: str, months: int) -> str | None:
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
    y, m = divmod(d.month - 1 + months, 12)
    y, m = d.year + y, m + 1
    # clamp to the last valid day of the target month (29 Feb + 12 months -> 28 Feb)
    for day in range(d.day, 27, -1):
        try:
            return date(y, m, day).isoformat()
        except ValueError:
            continue
    return date(y, m, d.day).isoformat()


def compute_deadline(facts: dict, limitation: dict) -> str | None:
    """Limitation expiry, computed in Python from the facts we have. None if no base date."""
    months = limitation.get("months")
    if not months:
        return None
    base = None
    if limitation.get("grievance") in ("illegal_termination", "gratuity"):
        base = facts.get("last_working_day")
    base = base or facts.get("date_of_cause") or facts.get("last_working_day")
    return _add_months(base, int(months)) if base else None


def pick_sections(text: str, keys: list[str]) -> list[dict]:
    """The labour_rules.json slice handed to the model, by grievance."""
    entries = load("labour_rules").get("sections", [])
    by_norm = {norm(e["id"]): e for e in entries}
    wanted: list[str] = []
    for key, _, ids in _TOPICS:
        if key in keys:
            wanted += ids
    forum_ids = pick_forum(keys).get("sections") or []

    slice_: list[dict] = []
    for sid in wanted + forum_ids + ALWAYS:
        hit = by_norm.get(norm(sid))
        if hit and hit not in slice_:
            slice_.append(hit)
    return slice_ or entries[:10]


def draft_labour(facts: dict, raw_text: str, today: str | None = None, extra: str = "") -> dict:
    from agent.sections import filter_sections  # lazy: import order independence

    today = today or date.today().isoformat()
    facts = facts or {}
    keys = grievances(raw_text, facts)
    forum = pick_forum(keys)
    limitation = pick_limitation(keys)
    deadline = compute_deadline(facts, limitation)
    slice_ = pick_sections(f"{raw_text} {facts.get('what_happened', '')}", keys)
    portal = (load("portals").get("labour") or {}) if _has("portals") else {}

    lean = [{"id": e["id"], "act": e.get("act", ""), "title": e.get("title", ""),
             "gist": e.get("gist", "")} for e in slice_]
    user = (
        f"Today's date is {today}.\n"
        f"grievances (decided in Python): {json.dumps(keys)}\n\n"
        f"FORUM, chosen in Python (use exactly this, do not pick another):\n"
        f"{json.dumps(forum, ensure_ascii=False, indent=1)}\n\n"
        f"LIMITATION, chosen in Python"
        + (f" (expires {deadline})" if deadline else " (no expiry date computable from the facts)")
        + f":\n{json.dumps(limitation, ensure_ascii=False, indent=1)}\n\n"
        f"FACTS JSON:\n{json.dumps(facts, ensure_ascii=False, indent=1)}\n\n"
        f"CLIENT'S OWN WORDS:\n{raw_text}\n\n"
        f"SECTIONS (cite only these ids):\n{json.dumps(lean, ensure_ascii=False, indent=1)}\n\n"
        f"PORTAL / PROCEDURE INFO:\n{json.dumps(portal, ensure_ascii=False, indent=1)}"
        + (f"\n\n{extra}" if extra else "")
    )
    out = client.ask(client.SONNET, prompts.load("draft_labour"), user,
                     json_mode=True, temperature=0.3)
    out = out if isinstance(out, dict) else {}

    kept, dropped = filter_sections("labour", out.get("sections") or [])
    return {
        "draft_markdown": out.get("draft_markdown", ""),
        "demand_letter_markdown": out.get("demand_letter_markdown") or "",
        "sections": kept,
        "sections_dropped": dropped,
        "what_to_carry": out.get("what_to_carry") or [],
        "next_steps": out.get("next_steps") or [],
        "hindi_summary": out.get("hindi_summary", ""),
        # the limitation is Python's to decide: the model's deadline_iso is discarded,
        # and "no date" is an honest answer when the facts carry no base date.
        "deadline_iso": deadline,
        "grievances": keys,
        "forum": forum,
        "limitation": limitation,
    }


def _has(name: str) -> bool:
    try:
        load(name)
        return True
    except (OSError, ValueError):
        return False
