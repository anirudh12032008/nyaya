"""Evidence checklist + annexure upload — offline (client.ask / ask_image monkeypatched)."""
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("NYAYA_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("NYAYA_UPLOADS", str(tmp_path / "uploads"))
    from db import db as _db
    importlib.reload(_db)
    _db.init()
    import agent.evidence as ev
    importlib.reload(ev)
    return _db


@pytest.fixture()
def case(db):
    cid = db.create_case({"module": "consumer", "client_name": "Ramesh",
                          "summary": "Phone stuck at service centre for 3 months.",
                          "draft_md": "# Complaint\n\nBody of the draft.",
                          "facts_json": '{"amount_inr": 40000}'})
    return db.get_case(cid)


def _patch(monkeypatch, checklist_items=None, label=None):
    from agent import client
    import agent.evidence as ev

    def fake_ask(model, system, user, json_mode=False, **kw):
        assert model == client.HAIKU
        if system == ev._CHECKLIST_SYS:
            return {"items": checklist_items or []}
        return dict(label or {})

    def fake_ask_image(model, system, prompt, image_bytes, mime="image/png", **kw):
        assert image_bytes
        return dict(label or {})

    monkeypatch.setattr(client, "ask", fake_ask)
    monkeypatch.setattr(client, "ask_image", fake_ask_image)


def test_checklist_puts_portal_documents_first_and_caps_at_eight(case, monkeypatch):
    import agent.evidence as ev
    from agent.data import load

    seed = load("portals")["consumer"]["documents"]
    # model replies out of order, repeats a portal item, and adds extras
    _patch(monkeypatch, checklist_items=[{"item": "Service centre job sheet", "why": "shows delay"},
                                         {"item": seed[1], "why": "proves purchase"}]
                                        + [{"item": f"Extra {i}", "why": "x"} for i in range(5)])

    rows = ev.checklist(case)

    assert [r["item"] for r in rows][:len(seed)] == seed
    assert rows[len(seed)]["item"] == "Service centre job sheet"
    assert rows[1]["why"] == "proves purchase"        # model's why wins for a seed item
    assert rows[0]["why"]                             # unmatched seed item still gets one
    assert len(rows) == ev.MAX_ITEMS
    assert all(r["have"] is False for r in rows)


def test_upload_labels_ticks_its_checklist_item_and_drops_invented_matches(case, db, monkeypatch):
    import agent.evidence as ev
    from agent.data import load

    seed = load("portals")["consumer"]["documents"]
    invoice = seed[1]
    _patch(monkeypatch, label={"label": "Invoice dated 12 Mar 2024", "kind": "invoice",
                               "summary": "Rs 40,000 phone purchase.", "matches_item": invoice})

    out = ev.label_upload(case["id"], "my invoice!.pdf", b"%PDF-1.4 fake", "application/pdf")

    assert out["matches_item"] == invoice
    row = db.list_annexures(case["id"])[0]
    assert row["filename"] == "my_invoice_.pdf"
    assert Path(row["path"]).read_bytes() == b"%PDF-1.4 fake"
    assert [r["have"] for r in ev.checklist(case)][1] is True

    # a match that is not on the candidate list is thrown away
    _patch(monkeypatch, label={"label": "Selfie", "kind": "photo", "summary": "A photo.",
                               "matches_item": "Affidavit of the Chief Justice"})
    out2 = ev.label_upload(case["id"], "pic.png", b"\x89PNG fake", "image/png")
    assert out2["matches_item"] == ""
    assert sum(r["have"] for r in ev.checklist(case)) == 1


def test_attach_annexure_index_is_idempotent(case, db, monkeypatch):
    import agent.evidence as ev

    assert ev.attach_annexure_index(case["id"]) is False  # nothing uploaded yet

    _patch(monkeypatch, label={"label": "Invoice", "kind": "invoice", "summary": "Bill.",
                               "matches_item": ""})
    ev.label_upload(case["id"], "bill.txt", b"invoice text", "text/plain")

    assert ev.attach_annexure_index(case["id"]) is True
    once = db.get_case(case["id"])["draft_md"]
    assert once.count(ev.MARKER) == 1
    assert "Annexure A-1" in once

    assert ev.attach_annexure_index(case["id"]) is False
    assert db.get_case(case["id"])["draft_md"] == once

    # a second annexure refreshes the same block instead of stacking another one
    ev.label_upload(case["id"], "photo.txt", b"photo notes", "text/plain")
    assert ev.attach_annexure_index(case["id"]) is True
    twice = db.get_case(case["id"])["draft_md"]
    assert twice.count(ev.MARKER) == 1
    assert "Annexure A-2" in twice
    assert twice.startswith("# Complaint")


def test_pdf_text_extraction_and_ui_import():
    import agent.evidence as ev
    import ui.evidence as ui_ev

    assert callable(ui_ev.render_evidence)
    assert ev.extract_text(b"plain bytes", "text/plain") == "plain bytes"
    assert ev.extract_text(b"\x00\xff not text", "image/png") == ""
