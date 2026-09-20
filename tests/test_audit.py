"""Per-case audit trail: timeline, model calls, PDF export. No API calls."""
import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRACE = [{"step": "classify", "model": "claude-haiku-4-5", "ms": 900, "cached": False},
         {"step": "draft_consumer", "model": "claude-sonnet-4-6", "ms": 4200, "cached": True}]


@pytest.fixture()
def wired(tmp_path, monkeypatch):
    monkeypatch.setenv("NYAYA_DB", str(tmp_path / "test.db"))
    from db import db as _db
    importlib.reload(_db)
    _db.init()

    from agent import audit as _audit
    importlib.reload(_audit)
    monkeypatch.setattr(_audit.client, "ask", lambda *a, **k: "Case handled by the clinic.")
    monkeypatch.setattr(_audit, "AUDIT_DIR", tmp_path / "audits")

    case_id = _db.create_case({
        "module": "consumer", "client_name": "Sita Devi", "urgency": "high",
        "summary": "Phone not repaired under warranty", "draft_md": "# Complaint\n\nFacts.",
        "deadline": "2027-01-01", "eligible_aid": 1, "eligibility_reason": "woman applicant",
        "intake_seconds": 5.1, "trace_json": TRACE,
        "council_json": {"agents": {"risk": {}, "evidence": {}}, "brief_md": "x", "ms": 1000},
    })
    _db.log_event(case_id, "verified", {"pass": False, "redrafted": True,
                                        "issues": [{"type": "section", "detail": "bad cite"}],
                                        "sections_dropped": ["2(47)"]})
    _db.log_event(case_id, "redrafted", {"issues_fixed": 1})
    return _db, _audit, case_id


def test_timeline_from_events(wired):
    db, audit_mod, case_id = wired
    a = audit_mod.build_audit(case_id)

    assert [e["type"] for e in a["timeline"]] == ["created", "verified", "redrafted"]
    assert all(e["ts"] for e in a["timeline"])
    assert "bad cite" in next(e["detail"] for e in a["timeline"] if e["type"] == "verified")
    assert a["case"]["client_name"] == "Sita Devi"
    assert a["verification"] == {"passed": False, "redrafted": True,
                                 "issues": [{"type": "section", "detail": "bad cite"}]}
    assert a["sections_dropped"] == ["2(47)"]
    assert a["council"]["ran"] and a["council"]["specialists"] == ["evidence", "risk"]
    assert a["council"]["model"]
    assert a["eligibility"] == {"eligible": True, "reason": "woman applicant"}
    assert a["plain_summary"] == "Case handled by the clinic."


def test_model_calls_from_trace_json(wired):
    _, audit_mod, case_id = wired
    calls = audit_mod.build_audit(case_id)["model_calls"]
    assert calls == TRACE
    assert calls[1]["cached"] is True


def test_export_pdf(wired):
    _, audit_mod, case_id = wired
    path = audit_mod.export_audit_pdf(case_id)
    assert path.name == f"case-{case_id}-audit.pdf" and path.exists()
    assert path.read_bytes()[:4] == b"%PDF" and path.stat().st_size > 1000


def test_persist_intake_logs_verification(tmp_path, monkeypatch):
    monkeypatch.setenv("NYAYA_DB", str(tmp_path / "p.db"))
    from db import db as _db
    importlib.reload(_db)
    _db.init()
    from agent import case_service, eligibility
    importlib.reload(case_service)
    monkeypatch.setattr(case_service.eligibility, "assess", lambda f, s="": {
        "eligible": True, "reason": "woman applicant"})
    monkeypatch.setattr(case_service, "db", _db)

    case_id = case_service.persist_intake("phone broke", {
        "classification": {"module": "consumer", "urgency": "high",
                           "facts": {"parties": [{"name": "Sita"}]}},
        "draft": {"draft_markdown": "# D", "sections": []},
        "trace": TRACE, "sections_dropped": ["2(47)"],
        "verification": {"pass": False, "issues": [], "redrafted": True, "first_issues": [{}]}})

    types = [e["type"] for e in _db.list_events(case_id)]
    assert "verified" in types and "redrafted" in types
    payload = json.loads(next(e["payload"] for e in _db.list_events(case_id)
                              if e["type"] == "verified"))
    assert payload["sections_dropped"] == ["2(47)"] and payload["redrafted"] is True
