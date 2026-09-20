"""Stage 5A: overnight batch triage + morning brief.

All `new` cases are re-classified for urgency and re-screened for legal-aid
eligibility in a 4-thread pool, then Sonnet writes the clinic head's morning
brief from a JSON summary computed here in Python. The model never counts.
"""
from __future__ import annotations

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from agent import classify as classify_mod
from agent import eligibility, prompts
from agent.client import SONNET, ask
from agent.sentinel import days_left, today
from db import db

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
WINDOW_DAYS = 30


def _case_text(c: dict) -> str:
    facts = c.get("facts_json")
    if isinstance(facts, str):
        try:
            facts = json.loads(facts)
        except ValueError:
            facts = {"raw": facts}
    parts = [c.get("summary") or ""]
    if isinstance(facts, dict):
        parts += [f"{k}: {v}" for k, v in facts.items() if v not in (None, "", [], {})]
    return "\n".join(p for p in parts if p).strip() or "(no summary recorded)"


def _triage_one(c: dict) -> dict:
    """Model calls only -- no DB writes (one shared sqlite connection)."""
    out = {"id": c["id"]}
    try:
        cls = classify_mod.classify(_case_text(c))
        out["urgency"] = cls.get("urgency") or c.get("urgency")
        facts = cls.get("facts") or {}
    except Exception as e:
        out["urgency"] = c.get("urgency")
        facts = {}
        out["error"] = f"classify: {type(e).__name__}"
    el = eligibility.assess(facts, c.get("summary") or "")   # never raises
    out["eligible_aid"] = 1 if el.get("eligible") else 0
    out["eligibility_reason"] = el.get("reason") or ""
    return out


def _payload() -> dict:
    s = db.stats()
    cases = db.list_cases()
    open_cases = [c for c in cases if (c.get("status") or "new") not in db.DONE]

    def row(c):
        return {"id": c["id"], "client": c.get("client_name"), "module": c.get("module"),
                "status": c.get("status"), "deadline": c.get("deadline"),
                "days_left": days_left(c.get("deadline"))}

    loads = {v["name"]: v["load"] for v in db.volunteers()}
    values = list(loads.values()) or [0]
    mx = max(values)
    mean = round(statistics.fmean(values), 2)
    overloaded = [n for n, l in loads.items() if l == mx and mx > mean]

    return {
        "simulated_today": today().isoformat(),
        "total_cases": s["total"],
        "counts_by_module": s["per_module"],
        "counts_by_status": s["per_status"],
        "urgent_cases": [row(c) for c in open_cases if (c.get("urgency") or "") == "high"],
        "deadlines_within_30_days": sorted(
            (row(c) for c in open_cases
             if (d := days_left(c.get("deadline"))) is not None and d <= WINDOW_DAYS),
            key=lambda r: r["days_left"]),
        "volunteer_load": loads,
        "max_load": mx,
        "mean_load": mean,
        "overloaded_volunteers": overloaded,
        "avg_intake_seconds": round(s["avg_intake_seconds"], 1),
        "feedback": {"up": s["feedback_up"], "down": s["feedback_down"]},
    }


def write_brief() -> str:
    payload = _payload()
    system = prompts.load("brief").replace(
        "{payload}", json.dumps(payload, ensure_ascii=False, indent=1))
    brief = ask(SONNET, system,
                "Write the morning brief for the clinic head now.",
                temperature=0.0, max_tokens=1200).strip()
    PUBLIC.mkdir(exist_ok=True)
    (PUBLIC / f"brief-{date.today().isoformat()}.md").write_text(brief, encoding="utf-8")
    return brief


def run_overnight(max_workers: int = 4) -> dict:
    t0 = time.time()
    new_cases = db.list_cases(status="new")
    results = []
    if new_cases:
        with ThreadPoolExecutor(max_workers=min(max_workers, 4)) as pool:
            results = list(pool.map(_triage_one, new_cases))

    for r in results:  # writes on the main thread; sqlite conn is shared
        db.update_case(r["id"], urgency=r.get("urgency"),
                       eligible_aid=r.get("eligible_aid"),
                       eligibility_reason=r.get("eligibility_reason"))
        db.log_event(r["id"], "triaged", {k: v for k, v in r.items() if k != "id"})

    return {"brief_md": write_brief(), "triaged": len(results),
            "seconds": round(time.time() - t0, 1)}


if __name__ == "__main__":
    out = run_overnight()
    print(f"triaged {out['triaged']} cases in {out['seconds']}s\n")
    print(out["brief_md"])
