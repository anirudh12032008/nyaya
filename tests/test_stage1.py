"""Stage 1 checks — no API key needed (agent.client.ask is monkeypatched)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import client, forum, sections  # noqa: E402


def test_forum_and_fee():
    d = forum.compute(40000)
    assert d["forum_id"] == "district" and d["fee_inr"] == 0, d
    d = forum.compute(1800000)
    assert d["forum_id"] == "district" and d["fee_inr"] == 400, d
    d = forum.compute(6500000)
    assert d["forum_id"] == "state" and d["fee_inr"] == 2000, d
    d = forum.compute(None)
    assert d["forum_id"] == "district" and d["fee_inr"] == 0 and d["amount_unknown"], d


def test_filter_drops_bogus_id():
    kept, dropped = sections.filter_sections(
        "consumer", [{"id": "Section 2(7)"}, {"id": "999"}])
    assert dropped == ["999"], (kept, dropped)
    assert [k["id"] for k in kept] == ["Section 2(7)"], kept


CANNED_CLASSIFY = {
    "module": "consumer", "jurisdiction": "Bhopal", "urgency": "medium", "language": "hinglish",
    "facts": {"parties": ["Client", "Service centre"], "amount_inr": 40000,
              "date_of_cause": "2026-01-01", "what_happened": "Phone stuck at service centre."},
    "missing_fact": None,
}
CANNED_DRAFT = {
    "draft_markdown": "# Consumer Complaint\n\n## 1. Complainant\n[TO CONFIRM]\n",
    "sections": [{"id": "2(11)", "why": "deficiency"}, {"id": "999", "why": "bogus"}],
    "next_steps": ["Collect the invoice"], "hindi_summary": "शिकायत तैयार है।",
    "deadline_iso": "2099-01-01",
}


def test_pipeline_drafts_and_drops(monkeypatch):
    def fake_ask(model, system, user, json_mode=False, temperature=0.0, **kw):
        return CANNED_CLASSIFY if model == client.HAIKU else CANNED_DRAFT

    monkeypatch.setattr(client, "ask", fake_ask)
    monkeypatch.setattr(client, "last_trace", lambda: {"model": "x", "ms": 1, "cached": True})
    from agent import pipeline

    r = pipeline.run_intake("Mera 40000 ka phone kharab hai, Jan 2026 mein liya tha.")
    assert r["forum"]["forum_id"] == "district" and r["forum"]["fee_inr"] == 0, r["forum"]
    assert r["draft"]["draft_markdown"].startswith("# Consumer Complaint"), r["draft"]
    assert r["sections_dropped"] == ["999"], r["sections_dropped"]
    assert [s["id"] for s in r["draft"]["sections"]] == ["2(11)"], r["draft"]["sections"]
    assert r["draft"]["deadline_iso"] == "2028-01-01", "Python must override the model's deadline"
    assert len(r["trace"]) == 2 and r["trace"][0]["step"] == "classify", r["trace"]


def test_pipeline_asks_one_question(monkeypatch):
    monkeypatch.setattr(client, "ask", lambda *a, **k: {**CANNED_CLASSIFY,
                                                       "missing_fact": "Kitne ka phone tha?"})
    monkeypatch.setattr(client, "last_trace", lambda: {"model": "x", "ms": 1, "cached": True})
    from agent import pipeline

    r = pipeline.run_intake("Phone kharab hai")
    assert r["missing_fact"] and r["draft"] is None, r


def test_pdf_renders():
    from pdf.render import draft_to_pdf
    out = draft_to_pdf("# Title\n\n- bullet\n\nमेरा फोन खराब है।", {"forum": "District", "fee_inr": 0})
    assert out[:4] == b"%PDF" and len(out) > 1000


if __name__ == "__main__":  # runnable without pytest
    class _MP:
        def __init__(self): self.undo = []
        def setattr(self, obj, name, val):
            self.undo.append((obj, name, getattr(obj, name)))
            setattr(obj, name, val)

    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        mp = _MP()
        try:
            fn(mp) if fn.__code__.co_argcount else fn()
            print(f"PASS {name}")
        except Exception as e:
            failures += 1
            print(f"FAIL {name}: {type(e).__name__}: {e}")
        finally:
            for obj, attr, val in reversed(mp.undo):
                setattr(obj, attr, val)
    sys.exit(1 if failures else 0)
