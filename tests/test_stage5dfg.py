"""Stage 5D+5F+5G checks — no API key needed (agent.client.ask is monkeypatched)."""
import importlib
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


def test_find_similar_drops_bogus_id_and_fills_from_db(db, monkeypatch):
    from agent import client
    from agent import similar

    real_case = db.list_cases()[0]
    bogus_id = max(c["id"] for c in db.list_cases()) + 999

    def fake_ask(model, system, user, json_mode=False, temperature=0.0, **kw):
        assert model == client.SONNET
        return {"similar": [{"case_id": real_case["id"], "why": "same module, similar facts"},
                             {"case_id": bogus_id, "why": "hallucinated case"}]}

    monkeypatch.setattr(client, "ask", fake_ask)

    out = similar.find_similar("Client's phone is stuck at the service centre.",
                               {"amount_inr": 40000}, k=3)

    assert [m["case_id"] for m in out] == [real_case["id"]], out
    assert out[0]["client_name"] == real_case.get("client_name", "")
    assert out[0]["module"] == real_case.get("module", "")
    assert out[0]["what_worked"] in ("worked", "in progress")


def test_find_similar_empty_summary_skips_api_call(db, monkeypatch):
    from agent import client, similar

    def boom(*a, **k):
        raise AssertionError("ask() must not be called for an empty summary")

    monkeypatch.setattr(client, "ask", boom)
    assert similar.find_similar("", {}) == []


def test_intake_extras_importable_and_no_streamlit_runtime_crash():
    # Importing must not need a live Streamlit runtime.
    import ui.intake_extras as extras

    assert callable(extras.render_mic)
    assert callable(extras.render_similar)
    assert callable(extras.render_autopilot)


def test_relief_extraction_from_draft_markdown():
    from ui.intake_extras import _relief_from_draft

    md = "# Complaint\n\n## Relief Sought\n1. Refund.\n2. Compensation.\n\n## Sections Relied\n2(7)\n"
    assert _relief_from_draft(md).startswith("1. Refund.")
    assert _relief_from_draft("no such section") == "[TO CONFIRM]"


def test_render_autopilot_skips_non_consumer_module():
    from unittest.mock import patch
    from ui.intake_extras import render_autopilot

    result = {"classification": {"module": "police", "facts": {}}, "draft": {}}
    with patch("streamlit.components.v1.html") as html_mock, patch("streamlit.markdown"):
        render_autopilot(result)
    html_mock.assert_not_called()


if __name__ == "__main__":  # runnable without pytest
    import types

    db_mod = importlib.import_module("db.db")
    import os
    os.environ["NYAYA_DB"] = "/tmp/nyaya_test5dfg.db"
    importlib.reload(db_mod)
    db_mod.init()

    from agent import client, similar

    real = db_mod.list_cases()[0]

    def fake_ask(model, system, user, json_mode=False, temperature=0.0, **kw):
        return {"similar": [{"case_id": real["id"], "why": "match"},
                             {"case_id": 999999, "why": "bogus"}]}

    client.ask = fake_ask
    out = similar.find_similar("test summary", {}, k=3)
    assert [m["case_id"] for m in out] == [real["id"]], out
    print("OK:", out)
