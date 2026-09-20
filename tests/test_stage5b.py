"""Stage 5B checks - verifier + one redraft, no API (agent.client.ask is monkeypatched)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import client  # noqa: E402

CLASSIFY = {"module": "consumer", "jurisdiction": "Bhopal", "urgency": "medium",
            "language": "hinglish", "missing_fact": None,
            "facts": {"parties": ["Client", "Service centre"], "amount_inr": 40000,
                      "date_of_cause": "2026-01-01", "what_happened": "Phone stuck."}}
BAD_DRAFT = {"draft_markdown": "# Complaint\n## 1. Complainant\n[TO CONFIRM]\n",
             "sections": [{"id": "2(11)", "why": "deficiency"}, {"id": "999", "why": "bogus"}],
             "next_steps": ["Collect invoice"], "hindi_summary": "", "deadline_iso": None}
GOOD_DRAFT = {**BAD_DRAFT, "draft_markdown": BAD_DRAFT["draft_markdown"] + "## 8. Verification\n",
              "sections": [{"id": "2(11)", "why": "deficiency in service"}]}
FAIL = {"pass": False, "issues": [{"type": "missing_part", "detail": "no Verification",
                                   "fix": "add Verification"}]}
OK = {"pass": True, "issues": []}


def _run(monkeypatch, replies):
    calls = []

    def fake_ask(model, system, user, json_mode=False, temperature=0.0, **kw):
        calls.append(user)
        return CLASSIFY if model == client.HAIKU else replies.pop(0)

    monkeypatch.setattr(client, "ask", fake_ask)
    monkeypatch.setattr(client, "last_trace", lambda: {"model": "x", "ms": 1, "cached": True})
    from agent import pipeline
    return pipeline.run_intake("Mera 40000 ka phone kharab hai."), calls


def test_fail_then_redraft_then_pass(monkeypatch):
    r, calls = _run(monkeypatch, [BAD_DRAFT, FAIL, GOOD_DRAFT, OK])
    v = r["verification"]
    assert v["redrafted"] is True and v["pass"] is True, v
    assert v["first_issues"] == FAIL["issues"] and v["issues"] == [], v
    steps = [t["step"] for t in r["trace"]]
    assert steps == ["classify", "draft_consumer", "verify", "redraft", "verify_2"], steps
    assert "## Reviewer issues to fix" in calls[3] and "no Verification" in calls[3]
    assert [s["id"] for s in r["draft"]["sections"]] == ["2(11)"]  # guard ran after redraft
    assert "## 8. Verification" in r["draft"]["draft_markdown"]


def test_pass_first_time_no_redraft(monkeypatch):
    r, _ = _run(monkeypatch, [GOOD_DRAFT, OK])
    v = r["verification"]
    assert v == {"pass": True, "issues": [], "redrafted": False, "first_issues": []}, v
    assert [t["step"] for t in r["trace"]] == ["classify", "draft_consumer", "verify"]
