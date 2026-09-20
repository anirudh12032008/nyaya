"""Stage 2: police complaint drafter (BNS/BNSS).

Section selection and the "did the station refuse?" decision happen in Python;
the model only writes prose over the slice it is handed.
"""
from __future__ import annotations

import json
import re
from datetime import date

from agent import client, prompts
from agent.data import load
from agent.sections import norm

# BNSS sections every police draft must see, whatever the offence.
ALWAYS = ["BNSS 173", "BNSS 173(1)", "BNSS 173(4)", "BNSS 175(3)"]

# offence keyword -> BNS/IT Act section ids to put in the slice
_TOPICS: list[tuple[str, list[str]]] = [
    (r"theft|chori|stolen|steal|churana|churaya|snatch", ["303", "304", "305", "317"]),
    (r"cheat|fraud|dhokha|thag|scam|upi|otp|phish", ["318", "319", "IT Act 66C", "IT Act 66D"]),
    (r"threat|dhamki|intimidat|jaan se", ["351"]),
    (r"assault|maar|peet|beat|hurt|hamla", ["115", "117", "131"]),
    (r"dowry|dahej", ["80", "85"]),
    (r"harass|chhed|molest|stalk|pareshan", ["74", "75", "78", "79"]),
    (r"trespass|ghus|break.?in", ["329"]),
]

_REFUSED = re.compile(
    r"refus|refuse|nahi likh|nahi li|nahi likhi|inkar|inkaar|mana kar|fir nahi|"
    r"declin|turned me away|register nahi|likhne se mana",
    re.I,
)


def station_refused(text: str, facts: dict | None = None) -> bool:
    """Keyword check over the client's words plus anything the classifier echoed back."""
    blob = text or ""
    if facts:
        if facts.get("station_refused") is True:
            return True
        blob += " " + json.dumps(facts, ensure_ascii=False)
    return bool(_REFUSED.search(blob))


def pick_sections(text: str) -> list[dict]:
    """Keyword heuristics over bns_sections.json -> the slice handed to the model."""
    entries = load("bns_sections").get("sections", [])
    by_norm = {norm(e["id"]): e for e in entries}

    wanted: list[str] = []
    for pattern, ids in _TOPICS:
        if re.search(pattern, text or "", re.I):
            wanted += ids
    slice_ = [] if wanted else [e for e in entries if e.get("act", "").startswith("BNS ")][:15]

    for sid in wanted + ALWAYS:
        hit = by_norm.get(norm(sid)) or next(
            (e for e in entries if norm(e["id"]).endswith(norm(sid))), None)
        if hit and hit not in slice_:
            slice_.append(hit)
    for sid in ALWAYS:  # the fallback slice still needs the BNSS four
        hit = next((e for e in entries if norm(e["id"]) == norm(sid)), None)
        if hit and hit not in slice_:
            slice_.append(hit)
    return slice_


def draft_police(facts: dict, raw_text: str, today: str | None = None) -> dict:
    from agent.sections import filter_sections  # lazy: import order independence

    today = today or date.today().isoformat()
    refused = station_refused(raw_text, facts)
    slice_ = pick_sections(f"{raw_text} {facts.get('what_happened', '')}")
    portal = (load("portals").get("police") or {}) if _has("portals") else {}

    lean = [{"id": e["id"], "title": e.get("title", ""), "gist": e.get("gist", ""),
             "cognizable": e.get("cognizable")} for e in slice_]
    user = (
        f"Today's date is {today}.\n"
        f"station_refused: {json.dumps(refused)}\n\n"
        f"FACTS JSON:\n{json.dumps(facts, ensure_ascii=False, indent=1)}\n\n"
        f"CLIENT'S OWN WORDS:\n{raw_text}\n\n"
        f"SECTIONS (cite only these ids):\n{json.dumps(lean, ensure_ascii=False, indent=1)}\n\n"
        f"PORTAL / PROCEDURE INFO:\n{json.dumps(portal, ensure_ascii=False, indent=1)}"
    )
    out = client.ask(client.SONNET, prompts.load("draft_police"), user,
                     json_mode=True, temperature=0.3)
    out = out if isinstance(out, dict) else {}

    kept, dropped = filter_sections("police", out.get("sections") or [])
    sp = out.get("sp_letter_markdown") or ""
    return {
        "draft_markdown": out.get("draft_markdown", ""),
        "sp_letter_markdown": sp if refused else "",
        "sections": kept,
        "sections_dropped": dropped,
        "what_to_carry": out.get("what_to_carry") or [],
        "next_steps": out.get("next_steps") or [],
        "hindi_summary": out.get("hindi_summary", ""),
        "deadline_iso": out.get("deadline_iso") or None,
        "station_refused": refused,
    }


def _has(name: str) -> bool:
    try:
        load(name)
        return True
    except (OSError, ValueError):
        return False
