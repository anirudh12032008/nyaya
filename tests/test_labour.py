"""Labour module checks - no API: agent.client.ask is monkeypatched with canned JSON.

Run: .venv/bin/python tests/test_labour.py     (or: pytest tests/test_labour.py)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import client, labour  # noqa: E402

TODAY = "2026-09-20"
FACTORY = ("Main Pithampur ki ek factory mein helper hoon, 3 mahine se salary nahi mili, "
           "12000 rupaye mahina, aur pichle hafte bina notice ke nikal diya.")
FACTS = {"what_happened": "Factory helper, three months' wages unpaid, dismissed without notice.",
         "employer": "Shree Industries, Pithampur", "monthly_wage_inr": 12000,
         "months_unpaid": 3, "date_of_cause": "2026-06-01", "last_working_day": "2026-09-12"}


def canned(payload):
    """Replace client.ask with a function returning `payload` and a fake trace."""
    def fake_ask(model, system, user, json_mode=False, temperature=0.0, **kw):
        client._last_trace = {"model": model, "ms": 1, "cached": False}
        fake_ask.last_user = user
        return payload if json_mode else json.dumps(payload)
    client.ask = fake_ask
    labour.client.ask = fake_ask
    return fake_ask


DRAFT = {
    "draft_markdown": "To the Authority under section 15, Payment of Wages Act...",
    "demand_letter_markdown": "To Shree Industries... pay within 15 days.",
    "sections": [{"id": "PWA 15", "why": "three wage periods unpaid"},
                 {"id": "ID Act 25F", "why": "no notice or retrenchment compensation"},
                 {"id": "IPC 420", "why": "hallucinated"},
                 {"id": "Labour Act 999", "why": "invented"}],
    "what_to_carry": ["ID card", "Wage slips"],
    "next_steps": ["No court fee for a worker's application."],
    "hindi_summary": "आपकी मजदूरी...",
    "deadline_iso": "2099-01-01",
}


# ---------------------------------------------------------------- grievance -> forum

def test_grievance_detection():
    assert labour.grievances(FACTORY)[0] == "unpaid_wages"
    assert "illegal_termination" in labour.grievances(FACTORY)
    assert labour.grievances("PF kat raha hai par UAN account mein jama nahi") == \
        ["pf_not_deposited"]
    assert labour.grievances("ESI deducted but never deposited") == ["esi_not_deposited"]
    assert labour.grievances("gratuity nahi mili after 8 years") == ["gratuity"]
    # nothing recognisable falls back to the Labour Commissioner's general bucket
    assert labour.grievances("kuch samajh nahi aa raha") == ["general"]


def test_forum_and_limitation_are_python_chosen():
    wages = labour.pick_forum(["unpaid_wages"])
    assert wages["id"] == "pwa_authority" and wages["source"]
    assert labour.pick_forum(["illegal_termination"])["id"] == "labour_court"
    assert labour.pick_forum(["pf_not_deposited"])["id"] == "epfo_regional"
    assert "Indore" in labour.pick_forum(["pf_not_deposited"])["where"]
    assert labour.pick_forum(["gratuity"])["id"] == "gratuity_controlling_authority"
    assert labour.pick_forum(["general"])["id"] == "labour_commissioner"
    assert labour.pick_forum(["nonsense"])["id"] == "labour_commissioner"

    assert labour.pick_limitation(["unpaid_wages"])["months"] == 12
    assert labour.pick_limitation(["illegal_termination"])["months"] == 36
    assert labour.pick_limitation(["below_minimum_wage"])["months"] == 6
    assert labour.pick_limitation(["pf_not_deposited"])["months"] is None
    assert all(e.get("source") for e in
               (labour.pick_limitation([k]) for k in ("unpaid_wages", "gratuity", "general")))


def test_deadline_computed_in_python():
    wages = labour.pick_limitation(["unpaid_wages"])
    assert labour.compute_deadline(FACTS, wages) == "2027-06-01"    # 12 months from cause
    term = labour.pick_limitation(["illegal_termination"])
    assert labour.compute_deadline(FACTS, term) == "2029-09-12"     # 3 years from last day
    assert labour.compute_deadline({}, wages) is None               # no base date -> no deadline
    assert labour.compute_deadline(FACTS, labour.pick_limitation(["pf_not_deposited"])) is None
    assert labour._add_months("2028-02-29", 12) == "2029-02-28"     # clamps a short month


# ---------------------------------------------------------------- drafter

def test_draft_labour_guards_sections_and_overrides_model_deadline():
    canned(DRAFT)
    out = labour.draft_labour(FACTS, FACTORY, TODAY)
    ids = [s["id"] for s in out["sections"]]
    assert "PWA 15" in ids and "ID Act 25F" in ids, ids
    assert "IPC 420" not in ids and "Labour Act 999" not in ids
    assert {"IPC 420", "Labour Act 999"} <= set(out["sections_dropped"]), out["sections_dropped"]
    assert out["demand_letter_markdown"], "the employer demand letter is always produced"
    # the model's deadline never wins over the Python computation
    assert out["deadline_iso"] == "2027-06-01" != DRAFT["deadline_iso"]
    assert out["forum"]["id"] == "pwa_authority"
    assert out["limitation"]["grievance"] == "unpaid_wages"
    assert out["what_to_carry"] == ["ID card", "Wage slips"]


def test_forum_is_handed_to_the_model_not_asked_of_it():
    ask = canned(DRAFT)
    labour.draft_labour({"what_happened": "PF deducted, not deposited"},
                        "PF kat raha hai par jama nahi hua", TODAY)
    user = ask.last_user
    assert "FORUM, chosen in Python" in user and "epfo_regional" in user
    assert "LIMITATION, chosen in Python" in user
    # the section slice is a whitelist, and only labour ids are in it
    assert "EPF 7A" in user and "BNSS" not in user


def test_pf_only_case_has_no_deadline():
    canned(DRAFT)
    out = labour.draft_labour({"date_of_cause": "2026-01-01"},
                              "EPF UAN mein paisa jama nahi hua", TODAY)
    assert out["forum"]["id"] == "epfo_regional"
    assert out["deadline_iso"] is None, "no statutory limitation for a s.7A inquiry"


# ---------------------------------------------------------------- wiring

def test_sections_guard_knows_the_module():
    from agent import sections
    ids = sections.valid_ids("labour")
    assert {"pwa 15", "id act 25f", "epf 7a", "esi 85"} <= ids, sorted(ids)
    kept, dropped = sections.filter_sections("labour", ["PWA 15", "s. PGA 4", "nope"])
    assert kept == ["PWA 15", "s. PGA 4"] and dropped == ["nope"]


def test_pipeline_modules_routes_labour():
    from agent import pipeline_modules
    assert "labour" in pipeline_modules.MODULES
    canned(DRAFT)
    trace = []
    out = pipeline_modules.run_module("labour", {"facts": FACTS}, FACTORY, TODAY, trace)
    assert out["forum"]["id"] == "pwa_authority"
    assert trace and trace[0]["step"] == "draft_labour" and "ms" in trace[0], trace


def test_run_intake_routes_labour_end_to_end():
    from agent import classify, pipeline, verify
    canned(DRAFT)

    def route(model, system, user, json_mode=False, temperature=0.0, **kw):
        client._last_trace = {"model": model, "ms": 1, "cached": False}
        if "intake classifier" in system:
            return {"module": "labour", "facts": FACTS, "urgency": "high", "language": "hinglish"}
        if "drafting a labour claim" in system:
            return DRAFT
        return {"pass": True, "issues": []}                     # the verifier
    client.ask = labour.client.ask = route   # classify/verify call client.ask by attribute

    r = pipeline.run_intake(FACTORY)
    assert r["classification"]["module"] == "labour"
    assert r["forum"] is None, "labour uses its own forum table, not the consumer one"
    assert r["draft"]["forum"]["id"] == "pwa_authority"
    assert set(r["sections_dropped"]) == {"IPC 420", "Labour Act 999"}
    assert [t["step"] for t in r["trace"]][:2] == ["classify", "draft_labour"]


def test_ui_and_guide_module_lists_include_labour():
    from agent import guide
    from ui import stage4
    from agent.data import load
    assert "labour" in guide.HI_MODULE
    assert "labour" in stage4.MODULES
    assert "labour" in load("portals")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
