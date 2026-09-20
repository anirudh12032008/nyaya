"""Stage 2 checks - no API: agent.client.ask is monkeypatched with canned JSON.

Run: .venv/bin/python tests/test_stage2.py     (or: pytest tests/test_stage2.py)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import client, police, tenant  # noqa: E402

TODAY = "2026-09-20"
BIKE = ("Police station refused to register my stolen bike complaint, "
        "bike worth 60k, stolen from hostel parking last week.")
AGREEMENT = (ROOT / "data" / "sample_rent_agreement.txt").read_text(encoding="utf-8")


def canned(payload):
    """Replace client.ask with a function returning `payload` and a fake trace."""
    def fake_ask(model, system, user, json_mode=False, temperature=0.0, **kw):
        client._last_trace = {"model": model, "ms": 1, "cached": False}
        return payload if json_mode else json.dumps(payload)
    client.ask = fake_ask
    police.client.ask = fake_ask
    tenant.client.ask = fake_ask


def test_heuristic_flags():
    ids = {f["rule_id"] for f in tenant.heuristic_flags(AGREEMENT)}
    assert {"REG-17", "MTA-11", "CA-74"} <= ids, ids
    # and the same text pasted as one long line still flags all three
    flat = {f["rule_id"] for f in tenant.heuristic_flags(AGREEMENT.replace("\n", " "))}
    assert {"REG-17", "MTA-11", "CA-74"} <= flat, flat
    # a clean agreement flags nothing
    assert tenant.heuristic_flags(
        "1. TERM. Eleven months from 1 April 2026, registered before the Sub-Registrar, Bhopal. "
        "2. RENT. Rs. 12,000 per month. 3. DEPOSIT. Rs. 24,000, being two months' rent.") == []


def test_station_refused():
    assert police.station_refused(BIKE) is True
    assert police.station_refused("thana wale FIR nahi likh rahe hain") is True
    assert police.station_refused("Mera phone chori ho gaya, complaint karni hai") is False
    assert police.station_refused("x", {"station_refused": True}) is True


def test_draft_police_sp_letter_and_dropped_section():
    canned({
        "draft_markdown": "To the SHO...",
        "sp_letter_markdown": "To the Superintendent of Police... under Section 173(4) BNSS.",
        "sections": [{"id": "303", "why": "bike taken dishonestly"},
                     {"id": "BNSS 173(4)", "why": "station refused to record"},
                     {"id": "IPC 999", "why": "hallucinated"}],
        "what_to_carry": ["RC book", "Aadhaar"],
        "next_steps": ["Zero-FIR may be lodged at any station under BNSS 173(1)."],
        "hindi_summary": "आपकी शिकायत...",
        "deadline_iso": None,
    })
    out = police.draft_police({"what_happened": BIKE}, BIKE, TODAY)
    ids = [s["id"] for s in out["sections"]]
    assert "BNSS 173(4)" in ids, ids
    assert "IPC 999" not in ids and "IPC 999" in out["sections_dropped"], out
    assert out["sp_letter_markdown"], "refusal in the text must yield an SP letter"
    assert out["station_refused"] is True
    assert out["what_to_carry"] == ["RC book", "Aadhaar"]

    # no refusal -> no SP letter even if the model produces one
    quiet = "Mera phone chori ho gaya hostel se, complaint karni hai."
    assert police.draft_police({"what_happened": quiet}, quiet, TODAY)["sp_letter_markdown"] == ""


def test_draft_tenant_merges_and_filters():
    canned({
        "flags": [{"clause": "8. NOTICE...", "issue": "one-sided notice period",
                   "rule_id": "MTA-NOTICE", "severity": "medium"},
                  {"clause": "made up", "issue": "invented", "rule_id": "NOPE-1",
                   "severity": "high"}],
        "draft_markdown": "To the landlord...",
        "sections": [{"id": "TPA-106", "why": "notice period"},
                     {"id": "FAKE-42", "why": "hallucinated"}],
        "next_steps": ["Send by registered post."],
        "hindi_summary": "आपके अनुबंध में...",
        "deadline_iso": "2026-10-05",
    })
    out = tenant.draft_tenant(AGREEMENT, {}, TODAY)
    rule_ids = {f["rule_id"] for f in out["flags"]}
    assert {"REG-17", "MTA-11", "CA-74"} <= rule_ids, rule_ids   # heuristics survive
    assert "MTA-NOTICE" in rule_ids                              # model flag merged in
    assert "NOPE-1" not in rule_ids                              # unknown rule dropped
    assert "NOPE-1" in out["sections_dropped"] and "FAKE-42" in out["sections_dropped"]
    sec_ids = {s["id"] for s in out["sections"]}
    assert "TPA-106" in sec_ids and rule_ids <= sec_ids          # every flag is a cited rule
    assert out["deadline_iso"] == "2026-10-05"


def test_pipeline_modules_traces():
    from agent import pipeline_modules
    canned({"draft_markdown": "x", "sp_letter_markdown": "", "sections": [],
            "what_to_carry": [], "next_steps": [], "hindi_summary": "", "deadline_iso": None})
    trace = []
    out = pipeline_modules.run_module("police", {"facts": {"what_happened": BIKE}},
                                      BIKE, TODAY, trace)
    assert out["draft_markdown"] == "x"
    assert trace and trace[0]["step"] == "draft_police" and "ms" in trace[0], trace


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
