"""Stage 3: DB, seeding, assignment, load accounting, stats, persistence."""
import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("NYAYA_DB", str(tmp_path / "test.db"))
    from db import db as _db
    importlib.reload(_db)
    _db.init()
    return _db


def test_seed(db):
    assert len(db.list_cases()) == 12
    assert len(db.volunteers()) == 4
    days = [db.days_to_deadline(c["deadline"]) for c in db.list_cases()]
    urgent = [d for d in days if d is not None and d < 30]
    assert len(urgent) == 3, f"expected 3 cases inside 30 days, got {urgent}"
    assert 9 in days, f"expected a case with 9 days left, got {sorted(d for d in days if d is not None)}"


def test_assign_lowest_load(db):
    before = {v["id"]: v["load"] for v in db.volunteers()}
    target = min(before, key=lambda i: (before[i], i))
    cid = db.create_case({"module": "consumer", "urgency": "low", "client_name": "Test Client"})
    case = db.get_case(cid)
    assert case["assigned_to"] == target
    assert {v["id"]: v["load"] for v in db.volunteers()}[target] == before[target] + 1


def test_filing_decrements_load(db):
    cid = db.create_case({"module": "police", "urgency": "high", "client_name": "X"})
    owner = db.get_case(cid)["assigned_to"]
    loaded = {v["id"]: v["load"] for v in db.volunteers()}[owner]
    db.update_case(cid, status="filed")
    assert db.get_case(cid)["status"] == "filed"
    assert {v["id"]: v["load"] for v in db.volunteers()}[owner] == loaded - 1
    assert any(e["type"] == "updated" for e in db.list_events(cid))


def test_reassign_moves_load(db):
    cid = db.create_case({"module": "tenant", "urgency": "low", "client_name": "Y"})
    old = db.get_case(cid)["assigned_to"]
    new = next(v["id"] for v in db.volunteers() if v["id"] != old)
    before = {v["id"]: v["load"] for v in db.volunteers()}
    db.update_case(cid, assigned_to=new)
    after = {v["id"]: v["load"] for v in db.volunteers()}
    assert after[old] == before[old] - 1 and after[new] == before[new] + 1


def test_stats_keys(db):
    db.add_feedback(1, "up", "good draft")
    db.add_feedback(2, "down", "wrong section")
    s = db.stats()
    for k in ("total", "per_module", "per_status", "per_volunteer",
              "avg_intake_seconds", "feedback_up", "feedback_down"):
        assert k in s, k
    assert s["feedback_up"] == 1 and s["feedback_down"] == 1
    assert len(db.list_feedback(1)) == 1


def test_persist_intake(db, monkeypatch):
    from agent import case_service, eligibility
    monkeypatch.setattr(eligibility, "assess", lambda facts, summary="": {
        "eligible": True, "category": "women", "reason": "woman applicant", "needs_info": False})

    result = {
        "classification": {"module": "consumer", "urgency": "high",
                           "facts": {"parties": ["Sunita Bai", "Acme Ltd"],
                                     "what_happened": "Phone not repaired under warranty."}},
        "draft": {"draft_markdown": "# Complaint", "sections": [{"id": "2(11)", "why": "deficiency"}],
                  "deadline_iso": "2027-01-01"},
        "trace": [{"step": "classify", "ms": 900}, {"step": "draft", "ms": 2100}],
    }
    cid = case_service.persist_intake("mera phone kharab hai", result)
    assert cid == 13
    case = db.get_case(cid)
    assert case["client_name"] == "Sunita Bai"
    assert case["eligible_aid"] == 1 and case["status"] == "new"
    assert case["intake_seconds"] == pytest.approx(3.0)
    assert case["assigned_to"] is not None
    assert 13 in [c["id"] for c in db.list_cases()]


def test_persist_intake_tolerates_empty(db, monkeypatch):
    from agent import case_service, eligibility
    monkeypatch.setattr(eligibility, "assess", lambda facts, summary="": {
        "eligible": False, "category": "", "reason": "no signal", "needs_info": True})
    cid = case_service.persist_intake("walk-in, nothing typed yet", {})
    assert db.get_case(cid)["client_name"] == "[TO CONFIRM]"
