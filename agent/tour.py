"""Guided tour: an agent that walks a new volunteer through Nyaya, page by page.

STEPS is the script (one entry per thing you actually do in the app); tour_turn()
answers free-form questions about the app, grounded in the current step and in what
is really in the database right now. No tools and no state mutation — the tour only
explains. Anything that touches a case goes through Ask Nyaya instead.
"""
from __future__ import annotations

from agent import client
from agent.client import HAIKU
from db import db

# Every "page" here must be a key in app.PAGES — tests/test_tour.py enforces that.
STEPS = [
    {"page": "Intake",
     "title": "Take a client's statement",
     "do": "Paste what the client said — Hindi, Hinglish or English — leave Module on "
           "'auto', and press Analyse. Attach a rent agreement PDF, or dictate with "
           "Voice intake, if you have either.",
     "why": "Claude classifies the matter (consumer / police / tenant), pulls out the "
            "facts, checks legal-aid eligibility and drafts the complaint. If one fact "
            "is missing it asks you a single question before drafting. Open the 'Agent "
            "trace' expander to see each model call and whether it was cached."},
    {"page": "Cases",
     "title": "Find the case in the queue",
     "do": "Filter by status, module or urgency, then pick the case from 'Open case'. "
           "A 🔴 flag means the limitation deadline is under 10 days, ⚠️ under 30.",
     "why": "Analysing an intake saves it as a case and auto-assigns it to the volunteer "
            "with the lightest load. The queue is the clinic's shared worklist."},
    {"page": "Cases",
     "title": "Read the draft and the sections it relies on",
     "do": "In the case detail, read the draft, then the 'Sections relied on' table and "
           "the legal-aid eligibility banner.",
     "why": "Every section id is checked against the clinic's statute data before it is "
            "shown, so the draft cannot cite a section that does not exist. The forum, "
            "the court fee and the limitation date are computed in Python, not guessed "
            "by the model."},
    {"page": "Cases",
     "title": "Run the review council",
     "do": "Scroll to the council section in the case detail and run it. It takes about "
           "a minute.",
     "why": "Five specialists review the case in parallel — evidence, the opponent's "
            "best counter, strategy, risk, and a plain-language letter for the client — "
            "and a synthesis agent merges them into one counsel brief. The brief is "
            "stored on the case, so it only runs once unless you force a re-run."},
    {"page": "Cases",
     "title": "Export, share, and record what the advocate changed",
     "do": "Download the PDF (it carries a QR back to this case), use 'Use as template' "
           "to start a similar intake, mark the case filed or reassign it, then leave 👍 "
           "or 👎 with a note.",
     "why": "The feedback notes are fed back as hints into later drafts, so correcting "
            "the model here makes the next draft better."},
    {"page": "Ask Nyaya",
     "title": "Ask the workspace agent",
     "do": "Pick a focus case in the sidebar and ask in plain language — 'which cases are "
           "closest to their deadline?', 'Rs 3.2 lakh ka claim hai, kaunsa forum?'",
     "why": "Ask Nyaya has tools over the real data: it lists and opens cases, searches "
            "the statutes, computes the consumer forum and fee, finds similar past cases, "
            "runs the council, and updates a case's status when you ask it to."},
    {"page": "Admin",
     "title": "Watch the clinic, not just the case",
     "do": "Check the metrics and the per-volunteer load, then look at 'Overnight triage' "
           "and 'Deadline sentinel'.",
     "why": "Triage classifies the new cases in a batch and writes a morning brief. The "
            "sentinel watches limitation dates and flags what is about to lapse."},
]

SYSTEM = """You are Nyaya's guide: you show a new legal-aid clinic volunteer how to use the
Nyaya app itself. You explain the software, not the law — if they ask a legal question, or
anything about a specific case, tell them to use the Ask Nyaya page, which has tools over the
real case data, and do not answer it yourself.

Be short. Two or three sentences, or a few bullets. Name the page and the button by the exact
label they will see on screen. Answer in the language they write in (Hindi, Hinglish or
English). Never invent a page, a button or a feature that is not in the tour script below —
if the app cannot do something, say so plainly.

THE APP, IN THE ORDER YOU WOULD USE IT:
{script}

WHERE THE USER IS NOW: step {n} of {total} — {here}

WHAT IS ACTUALLY IN THE WORKSPACE RIGHT NOW: {state}"""


def _script() -> str:
    return "\n".join(
        f"{i}. [{s['page']}] {s['title']} — do: {s['do']} why: {s['why']}"
        for i, s in enumerate(STEPS, 1))


def _state() -> str:
    """One line of real numbers, so the guide can say 'you have no cases yet, start at Intake'."""
    try:
        s = db.stats()
    except Exception as exc:
        return f"(could not read the database: {exc})"
    if not s["total"]:
        return "No cases yet — the queue is empty, so start at Intake."
    per_status = ", ".join(f"{v} {k}" for k, v in sorted(s["per_status"].items()))
    return f"{s['total']} cases ({per_status}); modules: {s['per_module'] or 'none'}."


def tour_turn(history: list[tuple[str, str]], user_text: str, step: int = 0) -> str:
    """Answer one question about the app. history is [(role, text), ...]; step indexes STEPS."""
    step = max(0, min(step, len(STEPS) - 1))
    here = f"{STEPS[step]['page']} — {STEPS[step]['title']}"
    system = SYSTEM.format(script=_script(), n=step + 1, total=len(STEPS),
                           here=here, state=_state())
    convo = "".join(f"{r.upper()}: {t}\n\n" for r, t in history[-8:])
    return client.ask(HAIKU, system, f"{convo}USER: {user_text}", max_tokens=1024)


if __name__ == "__main__":
    import sys
    print(tour_turn([], " ".join(sys.argv[1:]) or "What do I do first?"))
