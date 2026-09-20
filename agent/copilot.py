"""Volunteer copilot: what to say on the phone, and what to do next, before the deadline.

plan(case, force=False) -> {"call_script": str, "next_actions": [{action, by_when, why}],
                            "risks": [str], "allowed_dates": [iso], "ran_at": iso}
One Opus call. Dates are computed here, never by the model: the model may only pick a
by_when out of `allowed_dates`, and anything else is snapped to the nearest allowed date.
Cached in cases.copilot_json like the council brief.
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta

from agent import client

OPUS = "claude-opus-5"

# how long before the limitation deadline each action should land
LEAD_DAYS = (21, 14, 7)

_SYSTEM = """You are the volunteer copilot at a legal-aid clinic in Madhya Pradesh, India.
A volunteer (a law student or junior advocate, not the supervising advocate) is about to phone
the client. Give them the words to say and the next three things to do.

Return ONLY this JSON object, no prose, no code fences:
{"call_script": str, "next_actions": [{"action": str, "by_when": str, "why": str}],
 "risks": [str]}

Rules:
- `call_script` is 8-12 lines the volunteer reads aloud on the phone. Alternate Hindi
  (Devanagari) and its English line, like "हिंदी line\\nEnglish line". Warm, plain words, no
  legal jargon, 6th-grade reading level. Say who is calling, what has happened so far, what
  the clinic needs from the client, and what happens next. Never promise an outcome.
- Exactly 3 `next_actions`, most urgent first. `action` is one concrete thing a volunteer or
  the client can do; `why` is one line tied to this case.
- `by_when` MUST be copied exactly from the ALLOWED DATES list in the packet. Never write any
  other date, never write a relative phrase.
- `risks`: 2-4 short lines — what could go wrong on this case (limitation, missing evidence,
  client's safety, retaliation, wrong forum). Procedure only, no legal advice; the supervising
  advocate reviews everything. Never invent facts: unknowns stay [TO CONFIRM]."""


def _iso(d) -> str | None:
    try:
        return date.fromisoformat(str(d)[:10]).isoformat()
    except (TypeError, ValueError):
        return None


def allowed_dates(deadline: str | None, today: date | None = None) -> list[str]:
    """The only by_when values the model may pick: deadline minus 21/14/7 days.

    Dates already past are clamped to today; without a deadline we work off a 60-day horizon.
    """
    today = today or date.today()
    end = _iso(deadline)
    end = date.fromisoformat(end) if end else today + timedelta(days=60)
    return sorted({max(today, end - timedelta(days=d)).isoformat() for d in LEAD_DAYS})


def _nearest(value, allowed: list[str]) -> str:
    """Snap a model-supplied by_when onto the allowed list (nearest in days, else the first)."""
    want = _iso(value)
    if want in allowed:
        return want
    if not want:
        return allowed[0]
    w = date.fromisoformat(want)
    return min(allowed, key=lambda a: abs((date.fromisoformat(a) - w).days))


def _packet(case: dict, similar: list[dict], allowed: list[str], days_left) -> str:
    council = ""
    if case.get("council_json"):
        try:
            council = (json.loads(case["council_json"]).get("brief_md") or "")[:2000]
        except (ValueError, TypeError):
            council = ""
    return (
        f"TODAY: {date.today().isoformat()}\n"
        f"MODULE: {case.get('module')}\nCLIENT: {case.get('client_name')}\n"
        f"URGENCY: {case.get('urgency')}\nSTATUS: {case.get('status')}\n"
        f"LIMITATION DEADLINE: {case.get('deadline') or '[TO CONFIRM]'}"
        f" (days left: {days_left if days_left is not None else '[TO CONFIRM]'})\n"
        f"ALLOWED DATES for by_when (pick one of these exactly): {json.dumps(allowed)}\n\n"
        f"SUMMARY: {case.get('summary')}\n\n"
        f"FACTS JSON:\n{case.get('facts_json') or '{}'}\n\n"
        f"DRAFT (trimmed):\n{(case.get('draft_md') or '[no draft]')[:3000]}\n\n"
        f"COUNSEL BRIEF:\n{council or '[no council brief yet]'}\n\n"
        f"SIMILAR PAST CASES AND HOW THEY ENDED:\n{json.dumps(similar, ensure_ascii=False, indent=1)}")


def _similar_for(case: dict) -> list[dict]:
    from agent import similar as similar_mod
    try:
        found = similar_mod.find_similar(case.get("summary") or "",
                                         json.loads(case.get("facts_json") or "{}"), k=3)
        # this case is already in the DB, so it matches itself — drop it or Opus reads a duplicate
        return [m for m in found if m["case_id"] != case.get("id")]
    except Exception:  # memory is a nice-to-have; never sink the plan over it
        return []


def plan(case: dict, force: bool = False) -> dict:
    """Load-or-run: stored copilot_json wins unless force. Persists when the case has an id."""
    if not force and case.get("copilot_json"):
        try:
            return json.loads(case["copilot_json"])
        except ValueError:
            pass

    from db import db
    days_left = db.days_to_deadline(case.get("deadline"))
    allowed = allowed_dates(case.get("deadline"))
    t0 = time.time()
    raw = client.ask(OPUS, _SYSTEM,
                     _packet(case, _similar_for(case), allowed, days_left), json_mode=True)
    raw = raw if isinstance(raw, dict) else {}

    actions = []
    for a in (raw.get("next_actions") or [])[:3]:
        if not isinstance(a, dict):
            continue
        actions.append({"action": str(a.get("action") or "").strip(),
                        "by_when": _nearest(a.get("by_when"), allowed),
                        "why": str(a.get("why") or "").strip()})

    out = {"call_script": str(raw.get("call_script") or "").strip(),
           "next_actions": actions,
           "risks": [str(r) for r in (raw.get("risks") or []) if str(r).strip()],
           "allowed_dates": allowed,
           "ms": int((time.time() - t0) * 1000),
           "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if case.get("id"):
        db.update_case(case["id"], copilot_json=json.dumps(out, ensure_ascii=False))
    return out
