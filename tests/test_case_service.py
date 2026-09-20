"""The drafters hang their covering letter and flags off result["draft"], not the top level."""
import json

from agent import case_service
from db import db


def _persist(draft, tmp_path, monkeypatch):
    monkeypatch.setenv("NYAYA_DB", str(tmp_path / "t.db"))
    db._conn = None
    db.init()
    result = {"classification": {"module": "police", "urgency": "high",
                                 "facts": {"parties": [{"name": "Ramesh K"}],
                                           "what_happened": "bike stolen"}},
              "draft": draft, "trace": []}
    return db.get_case(case_service.persist_intake("bike stolen", result))


def test_sp_letter_and_flags_persist(tmp_path, monkeypatch):
    row = _persist({"draft_markdown": "body", "sp_letter_markdown": "LETTER TO SP",
                    "flags": ["FIR-REFUSED"], "sections": []}, tmp_path, monkeypatch)
    assert "LETTER TO SP" in row["draft_md"]
    assert json.loads(row["facts_json"])["flags"] == ["FIR-REFUSED"]


def test_labour_demand_letter_persists(tmp_path, monkeypatch):
    row = _persist({"draft_markdown": "claim", "demand_letter_markdown": "DEMAND",
                    "sections": []}, tmp_path, monkeypatch)
    assert "DEMAND" in row["draft_md"]
