"""Per-case audit trail for legal-aid funders / DLSA.

build_audit(case_id) assembles everything from the DB row, the events table and
trace_json in Python; only `plain_summary` is written by a model, and only from
those structured facts.
"""
from __future__ import annotations

import json
from pathlib import Path

from agent import client
from db import db

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "public" / "audits"

_SUMMARY_SYSTEM = """You write one paragraph for a legal-aid funder (DLSA) audit report.

HARD RULE: you may only restate the structured facts given below. Do not add a claim,
number, date, name, outcome or judgement that is not in them. If something is absent,
say it is not recorded. No speculation, no advice, no praise.

Write 6-8 plain-English sentences, one paragraph, no headings, no bullets, no markdown:
what the case is, how it was handled, which automated checks ran and what they found,
and what the record says about free-legal-aid eligibility."""


def _loads(raw, default):
    try:
        return json.loads(raw) if raw else default
    except (ValueError, TypeError):
        return default


def _detail(type: str, payload) -> str:
    if payload in (None, "", "null"):
        return ""
    data = _loads(payload, payload)
    if isinstance(data, dict):
        return ", ".join(f"{k}={v}" for k, v in data.items() if v not in (None, "", [], {}))[:300]
    return str(data)[:300]


def build_audit(case_id: int) -> dict:
    case = db.get_case(case_id)
    if not case:
        raise ValueError(f"no case #{case_id}")

    events = db.list_events(case_id)
    trace = _loads(case.get("trace_json"), [])
    council = _loads(case.get("council_json"), {}) or {}

    verified = next((e for e in reversed(events) if e["type"] == "verified"), None)
    v = _loads(verified["payload"], {}) if verified else {}

    audit = {
        "case": {k: case.get(k) for k in ("id", "created_at", "module", "status", "urgency",
                                          "client_name", "summary", "deadline",
                                          "intake_seconds")},
        "timeline": [{"ts": e["ts"], "type": e["type"], "detail": _detail(e["type"], e["payload"])}
                     for e in events],
        "model_calls": [{"step": s.get("step", ""), "model": s.get("model", ""),
                         "ms": s.get("ms", 0), "cached": bool(s.get("cached"))}
                        for s in trace if isinstance(s, dict)],
        "verification": {"passed": v.get("pass"), "issues": v.get("issues") or [],
                         "redrafted": bool(v.get("redrafted"))},
        "sections_dropped": v.get("sections_dropped") or [],
        "council": {"ran": bool(council.get("agents")),
                    "specialists": sorted(council.get("agents") or {}), "model": ""},
        "eligibility": {"eligible": bool(case.get("eligible_aid")),
                        "reason": case.get("eligibility_reason") or ""},
    }
    if audit["council"]["ran"]:  # orchestra stores no per-agent model; name the council's models
        from agent.orchestra import SPECIALISTS
        audit["council"]["model"] = ", ".join(sorted(
            {SPECIALISTS[n][0] for n in audit["council"]["specialists"] if n in SPECIALISTS}))
    audit["plain_summary"] = _plain_summary(audit)
    return audit


def _plain_summary(audit: dict) -> str:
    facts = {k: audit[k] for k in ("case", "verification", "sections_dropped", "council",
                                   "eligibility")}
    facts["events"] = [{"ts": e["ts"], "type": e["type"]} for e in audit["timeline"]]
    facts["model_calls"] = audit["model_calls"]
    user = "STRUCTURED FACTS (the only thing you may restate):\n" + json.dumps(
        facts, ensure_ascii=False, indent=1, default=str)
    try:
        return str(client.ask(client.HAIKU, _SUMMARY_SYSTEM, user, temperature=0.0,
                              max_tokens=700)).strip()
    except Exception as e:  # audit still ships without the model
        return f"[plain-English summary unavailable: {type(e).__name__}]"


def _models(audit: dict) -> str:
    return ", ".join(sorted({s["model"] for s in audit["model_calls"] if s["model"]})) or "none recorded"


def render_audit_md(audit: dict) -> str:
    c, v = audit["case"], audit["verification"]
    out = [f"# Audit trail — case #{c.get('id')} · {c.get('client_name')}", "",
           f"Module: {c.get('module')} · status: {c.get('status')} · urgency: {c.get('urgency')}",
           f"Opened: {c.get('created_at')} · limitation: {c.get('deadline') or '[none recorded]'}",
           f"Intake time: {(c.get('intake_seconds') or 0):.1f}s", "",
           "## Plain summary", "", audit.get("plain_summary") or "", "",
           "## Legal aid eligibility", "",
           f"- Eligible: {audit['eligibility']['eligible']}",
           f"- Reason: {audit['eligibility']['reason'] or '[not recorded]'}", "",
           "## Timeline", ""]
    for e in audit["timeline"]:
        out.append(f"- {e['ts']} · **{e['type']}** · {e['detail']}")
    out += ["", "## Model calls", ""]
    for s in audit["model_calls"]:
        out.append(f"- {s['step']} · {s['model']} · {s['ms']} ms"
                   + (" · cached" if s["cached"] else ""))
    out += ["", "## Verification", "",
            f"- Passed: {v['passed']}", f"- Redrafted: {v['redrafted']}"]
    for i in v["issues"]:
        out.append(f"- Issue [{i.get('type')}]: {i.get('detail')}")
    if audit["sections_dropped"]:
        out += ["", "## Sections dropped by the citation guard", ""]
        out += [f"- {s}" for s in audit["sections_dropped"]]
    out += ["", "## Review council", "",
            f"- Ran: {audit['council']['ran']}",
            f"- Specialists: {', '.join(audit['council']['specialists']) or 'none'}"]
    return "\n".join(out)


def export_audit_pdf(case_id: int) -> Path:
    from datetime import datetime

    from pdf.render import draft_to_pdf
    audit = build_audit(case_id)
    md = render_audit_md(audit) + (
        f"\n\nGenerated by Nyaya, {datetime.now().isoformat(timespec='seconds')}, "
        f"models: {_models(audit)}")
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    path = AUDIT_DIR / f"case-{case_id}-audit.pdf"
    path.write_bytes(draft_to_pdf(md, {"forum": f"Nyaya audit trail — case #{case_id}"}))
    return path
