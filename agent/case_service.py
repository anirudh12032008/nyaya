"""Turn a pipeline result into a persisted case row."""
from __future__ import annotations

import json

from agent import eligibility
from db import db


def _client_name(facts: dict) -> str:
    parties = facts.get("parties") or []
    if isinstance(parties, (str, bytes)):
        parties = [parties]
    for p in parties:
        name = (p.get("name") if isinstance(p, dict) else str(p)).strip() if p else ""
        if name:
            return name
    return "[TO CONFIRM]"


def persist_intake(text: str, result: dict) -> int:
    """Build a case from a `pipeline.run_intake` result and store it. Returns the id."""
    result = result or {}
    cls = result.get("classification") or {}
    facts = cls.get("facts") or {}
    draft = result.get("draft") or {}
    trace = result.get("trace") or []

    summary = (facts.get("what_happened") or text or "")[:200]
    draft_md = draft.get("draft_markdown") or ""
    # the drafters return their covering letter alongside the draft, not at the top level
    for letter in ("sp_letter_markdown", "demand_letter_markdown"):
        if draft.get(letter):
            draft_md += "\n\n---\n\n" + draft[letter]

    verdict = eligibility.assess(facts, summary)
    payload = dict(facts)
    if draft.get("flags"):
        payload["flags"] = draft["flags"]

    case_id = db.create_case({
        "module": cls.get("module") or "other",
        "status": "new",
        "urgency": cls.get("urgency") or "medium",
        "client_name": _client_name(facts),
        "summary": summary,
        "draft_md": draft_md,
        "sections_json": json.dumps(draft.get("sections") or [], ensure_ascii=False),
        "deadline": draft.get("deadline_iso"),
        "eligible_aid": int(bool(verdict["eligible"])),
        "eligibility_reason": verdict["reason"],
        "intake_seconds": sum(s.get("ms", 0) or 0 for s in trace) / 1000.0,
        "trace_json": json.dumps(trace, ensure_ascii=False, default=str),
        "facts_json": json.dumps(payload, ensure_ascii=False, default=str),
    })

    v = result.get("verification") or {}
    if v:  # audit trail: the reviewer's verdict happens before the case row exists
        db.log_event(case_id, "verified", {"pass": v.get("pass"), "issues": v.get("issues") or [],
                                           "redrafted": bool(v.get("redrafted")),
                                           "sections_dropped": result.get("sections_dropped") or []})
        if v.get("redrafted"):
            db.log_event(case_id, "redrafted", {"issues_fixed": len(v.get("first_issues") or [])})
    return case_id
