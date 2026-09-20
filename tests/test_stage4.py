"""Stage 4: QR, feedback -> prompt hints, public guide generation, template blanking."""
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NOTES = ["Relief Sought was too vague - ask for a specific refund amount",
         "Relief Sought was too vague - ask for a specific refund amount",
         "Verification paragraph missing the place and date"]


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("NYAYA_DB", str(tmp_path / "test.db"))
    from db import db as _db
    importlib.reload(_db)
    _db.init()
    import agent.learn
    importlib.reload(agent.learn)
    return _db


def test_make_qr_png():
    from pdf.qr import case_url, make_qr_png, qr_for_case
    assert make_qr_png("http://x/?case=1")[:4] == b"\x89PNG"
    assert qr_for_case(3)[:4] == b"\x89PNG"
    assert "case=3" in case_url(3) and "clinic=nliu" in case_url(3)


def test_base_url_from_env(monkeypatch):
    monkeypatch.setenv("NYAYA_BASE_URL", "https://nyaya.example/")
    import pdf.qr
    assert pdf.qr.case_url(2).startswith("https://nyaya.example/?case=2")


def test_top_corrections(db):
    from agent import learn
    cid = next(c["id"] for c in db.list_cases(module="consumer"))
    other = next(c["id"] for c in db.list_cases(module="tenant"))
    for n in NOTES:
        db.add_feedback(cid, "down", n)
    db.add_feedback(other, "down", "tenant-only note that must not leak")

    top = learn.top_corrections("consumer", 3)
    assert top[0] == NOTES[0], top                 # the twice-reported one ranks first
    assert NOTES[2] in top
    assert not any("tenant-only" in t for t in top)
    assert all("tenant-only" not in t for t in learn.top_corrections("consumer"))
    assert learn.top_corrections("tenant")[0].startswith("tenant-only")


def test_apply_hints_idempotent(db, tmp_path, monkeypatch):
    from agent import learn
    prompt = tmp_path / "draft_consumer.md"
    prompt.write_text("BASE PROMPT\n", encoding="utf-8")
    monkeypatch.setattr(learn, "PROMPTS", tmp_path)

    cid = next(c["id"] for c in db.list_cases(module="consumer"))
    for n in NOTES:
        db.add_feedback(cid, "down", n)

    old, new = learn.apply_hints("consumer")
    assert old == "BASE PROMPT\n"
    assert new.count("## Learned") == 1
    for n in set(NOTES):
        assert f"- {n}" in new

    old2, new2 = learn.apply_hints("consumer")          # running twice must not duplicate
    assert old2 == new == new2
    assert new2.count("## Learned") == 1
    assert new2.count("BASE PROMPT") == 1
    assert prompt.read_text(encoding="utf-8") == new2


def test_guide_generate_writes_file(tmp_path, monkeypatch):
    from agent import guide
    monkeypatch.setattr(guide, "PUBLIC", tmp_path)
    monkeypatch.setattr(guide.client, "ask",
                        lambda *a, **k: {"en": "English guide body. " + guide.CTA,
                                         "hi": "हिंदी मार्गदर्शिका। " + guide.CTA})

    out = guide.generate("consumer")
    assert out["en"].startswith("English guide")
    written = (tmp_path / "consumer.md").read_text(encoding="utf-8")
    assert "English guide body" in written and "हिंदी मार्गदर्शिका" in written
    assert guide.CTA in written
    assert "हिंदी" in guide.read("consumer")["hi"]      # round-trips per language

    # second call is served from the file, not the model
    monkeypatch.setattr(guide.client, "ask",
                        lambda *a, **k: pytest.fail("generate() should have used the cache"))
    assert guide.generate("consumer")["en"].startswith("English guide")


def test_template_prefill_blanks_facts(db):
    from ui import stage4
    case = db.get_case(next(c["id"] for c in db.list_cases(module="consumer")))
    text = stage4.template_prefill(case)
    assert "[NAME]" in text and "[AMOUNT]" in text and "[DATE]" in text
    assert case["client_name"] not in text
