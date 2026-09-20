"""Outcome learning + volunteer copilot — offline (agent.client.ask is monkeypatched)."""
import importlib
import json
import sys
from datetime import date, timedelta
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


def test_set_outcome_roundtrip_and_validation(db):
    cid = db.list_cases()[0]["id"]
    db.set_outcome(cid, "settled", "Opposite party refunded before the first hearing.")
    row = db.get_case(cid)
    assert row["outcome"] == "settled"
    assert row["outcome_note"].startswith("Opposite party refunded")
    assert row["outcome_at"]

    db.set_outcome(cid, None)  # clearing wipes the note and the timestamp
    assert db.get_case(cid)["outcome"] is None
    assert db.get_case(cid)["outcome_at"] is None

    with pytest.raises(ValueError):
        db.set_outcome(cid, "mostly won")


def test_seed_history_has_outcomes(db):
    assert sum(1 for c in db.list_cases() if c.get("outcome")) >= 3


def test_find_similar_uses_real_outcome(db, monkeypatch):
    from agent import client, similar

    cid = db.list_cases()[0]["id"]
    db.set_outcome(cid, "won", "Dated WhatsApp chat decided it.")
    seen = {}

    def fake_ask(model, system, user, json_mode=False, temperature=0.0, **kw):
        seen["system"] = system
        return {"similar": [{"case_id": cid, "why": "same module"}]}

    monkeypatch.setattr(client, "ask", fake_ask)
    out = similar.find_similar("Phone stuck at the service centre.", {"amount_inr": 40000}, k=3)

    assert out[0]["what_worked"] == "won"            # the column, not the status guess
    assert out[0]["outcome_note"] == "Dated WhatsApp chat decided it."
    assert "Dated WhatsApp chat decided it." in seen["system"]   # slim summaries carry it

    db.set_outcome(cid, None)                        # NULL outcome keeps the old behaviour
    out = similar.find_similar("Phone stuck at the service centre.", {}, k=3)
    assert out[0]["what_worked"] in ("worked", "in progress")


def test_learned_section_picks_up_outcome_notes(db):
    from agent import learn

    cid = next(c["id"] for c in db.list_cases(module="consumer"))
    db.set_outcome(cid, "won", "Attach the DGCA grievance ticket to the complaint.")
    try:
        assert "Attach the DGCA grievance ticket to the complaint." in learn.outcome_lessons("consumer")
        old, new = learn.apply_hints("consumer")
        assert "Attach the DGCA grievance ticket" in new
        assert learn.apply_hints("consumer")[1] == new  # idempotent
    finally:
        learn.prompt_path("consumer").write_text(old, encoding="utf-8")


def test_plan_by_when_guard_snaps_to_allowed_dates(db, monkeypatch):
    from agent import client, copilot

    deadline = (date.today() + timedelta(days=90)).isoformat()
    cid = db.create_case({"module": "consumer", "client_name": "Test Client",
                          "summary": "Refund refused.", "deadline": deadline,
                          "draft_md": "x" * 5000})
    case = db.get_case(cid)
    allowed = copilot.allowed_dates(deadline)
    assert len(allowed) == 3

    calls = []

    def fake_ask(model, system, user, json_mode=False, **kw):
        calls.append((model, user))
        if "case-memory assistant" in system:          # similar.py's prompt
            return {"similar": []}
        assert model == copilot.OPUS and json_mode
        return {"call_script": "नमस्ते\nHello", "risks": ["limitation is close"],
                "next_actions": [
                    {"action": "Collect the invoice", "by_when": allowed[1], "why": "proof"},
                    {"action": "Call the client", "by_when": "2099-01-01", "why": "confirm"},
                    {"action": "Draft the notice", "by_when": "next week", "why": "filing"},
                    {"action": "Extra action", "by_when": allowed[0], "why": "dropped"}]}

    monkeypatch.setattr(client, "ask", fake_ask)
    out = copilot.plan(case)

    assert [a["by_when"] for a in out["next_actions"]] == [allowed[1], allowed[-1], allowed[0]]
    assert len(out["next_actions"]) == 3              # capped at 3
    assert json.dumps(allowed) in calls[-1][1]        # the packet fixes the choices
    assert "x" * 3000 in calls[-1][1] and "x" * 3001 not in calls[-1][1]   # draft trimmed

    # persisted, and a second call replays the cache without touching the API
    assert json.loads(db.get_case(cid)["copilot_json"])["call_script"] == out["call_script"]
    monkeypatch.setattr(client, "ask", lambda *a, **k: pytest.fail("cached plan must not call"))
    assert copilot.plan(db.get_case(cid))["call_script"] == out["call_script"]


def test_allowed_dates_never_in_the_past():
    past = (date.today() - timedelta(days=5)).isoformat()
    assert copilot_dates(past) == [date.today().isoformat()]


def copilot_dates(deadline):
    from agent import copilot
    return copilot.allowed_dates(deadline)
