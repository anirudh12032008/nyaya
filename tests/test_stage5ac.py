"""Stage 5A/5C: overnight triage, morning brief, deadline sentinel."""
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def wired(tmp_path, monkeypatch):
    monkeypatch.setenv("NYAYA_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("NYAYA_CLOCK", str(tmp_path / "clock.json"))
    from db import db as _db
    importlib.reload(_db)
    _db.init()

    from agent import classify as classify_mod, client, eligibility, sentinel, triage
    monkeypatch.setattr(classify_mod, "classify",
                        lambda text, today=None: {"urgency": "high", "facts": {"parties": ["X"]}})
    monkeypatch.setattr(triage.classify_mod, "classify", classify_mod.classify)
    monkeypatch.setattr(eligibility, "assess", lambda facts, summary="": {
        "eligible": True, "category": "women", "reason": "woman applicant", "needs_info": False})
    monkeypatch.setattr(triage, "ask", lambda *a, **k: "Morning brief. 12 cases open.\n\n- Call #1")
    monkeypatch.setattr(triage, "PUBLIC", tmp_path / "public")
    return _db, sentinel, triage


def test_run_overnight(wired):
    db, _, triage = wired
    new_before = len(db.list_cases(status="new"))
    assert new_before >= 3

    out = triage.run_overnight()
    assert out["triaged"] == new_before
    assert "Morning brief" in out["brief_md"] and out["seconds"] >= 0
    assert list((triage.PUBLIC).glob("brief-*.md")), "brief not saved to public/"

    for c in db.list_cases(status="new"):
        assert c["urgency"] == "high"
        assert c["eligible_aid"] == 1
        assert c["eligibility_reason"] == "woman applicant"
        assert any(e["type"] == "triaged" for e in db.list_events(c["id"]))


def test_payload_is_computed_in_python(wired):
    db, _, triage = wired
    p = triage._payload()
    assert p["total_cases"] == len(db.list_cases())
    assert p["max_load"] >= p["mean_load"]
    assert all(r["days_left"] <= 30 for r in p["deadlines_within_30_days"])


def test_clock_advance_and_reset(wired):
    _, sentinel, _ = wired
    base = sentinel.today()
    assert sentinel.offset_days() == 0
    assert (sentinel.advance_clock(30) - base).days == 30
    assert sentinel.offset_days() == 30
    assert sentinel.reset_clock() == base


def test_pending_notifications(wired):
    db, sentinel, _ = wired
    sentinel.advance_clock(30)
    pending = sentinel.pending_notifications()
    assert len(pending) >= 3, pending
    for n in pending:
        assert n["message"].startswith(f"Namaste {n['client']} ji,")
        assert "NLIU Legal Aid Clinic, Bhopal" in n["message"]
        assert f"#{n['case_id']}" in n["message"]
        assert n["days_left"] <= 30
        assert db.get_case(n["case_id"])["status"] not in db.DONE
    overdue = [n for n in pending if n["days_left"] < 0]
    assert overdue and all("khatam ho chuki hai" in n["message"] for n in overdue)
    assert all("din baaki" in n["message"] for n in pending if n["days_left"] >= 0)

    sentinel.reset_clock()
    assert len(sentinel.pending_notifications()) < len(pending)
