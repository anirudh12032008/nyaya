"""Orchestra: a council of specialist Claude agents that review one case in parallel.

run_council(case, on_agent_done=None) -> dict
  Five specialists run concurrently (each one `client.ask` call, cached like the
  rest of the pipeline), then a synthesiser turns their JSON into one counsel
  brief. Result shape:
    {"agents": {name: {...}}, "brief_md": str, "ms": int, "ran_at": iso, "errors": {name: str}}
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from agent import client

OPUS = "claude-opus-5"
SONNET = "claude-sonnet-5"

_BASE = ("You are one specialist on a legal-aid clinic's review council in Madhya Pradesh, India. "
         "You get a case packet (facts, the junior's draft, statute sections). Never invent facts: "
         "anything unknown is written as [TO CONFIRM]. Procedure only, no legal advice beyond "
         "procedure; a supervising advocate reviews everything. Return ONLY the JSON object asked "
         "for, no prose, no code fences.")

# name -> (model, system prompt)
SPECIALISTS: dict[str, tuple[str, str]] = {
    "evidence": (SONNET, _BASE + """
Role: EVIDENCE OFFICER. Build the proof file.
Schema: {"have": [{"item": str, "why_it_matters": str}],
         "need": [{"item": str, "how_to_get": str, "blocking": bool}],
         "questions_for_client": [str]}
`have` = evidence the packet already shows exists; `need` = what must be collected before filing."""),
    "opponent": (OPUS, _BASE + """
Role: DEVIL'S ADVOCATE. You are the opposite party's lawyer.
Schema: {"their_strongest_arguments": [{"argument": str, "likely_basis": str}],
         "our_rebuttals": [{"to": str, "rebuttal": str, "needs_evidence": str}],
         "weakest_point_in_our_draft": str,
         "settlement_likelihood": "low|medium|high", "settlement_reason": str}"""),
    "strategy": (OPUS, _BASE + """
Role: FILING STRATEGIST. Turn the draft into a dated action plan.
Schema: {"steps": [{"day": int, "action": str, "who": "client|volunteer|advocate", "output": str}],
         "critical_dates": [{"date_iso": str, "what": str}],
         "escalation_path": [str],
         "total_est_days_to_filing": int}
Day 0 is TODAY from the packet. Use the packet's limitation deadline; do not compute your own."""),
    "risk": (SONNET, _BASE + """
Role: RISK & TRIAGE OFFICER.
Schema: {"urgency": "high|medium|low", "urgency_reason": str,
         "red_flags": [{"flag": str, "severity": "high|medium|low", "action": str}],
         "vulnerability_notes": [str],
         "refer_out": {"needed": bool, "to": str, "why": str}}
Red flags include: near limitation, safety of the client, retaliation risk, criminal overlap,
missing party details, amounts that change forum."""),
    "client_letter": (SONNET, _BASE + """
Role: CLIENT COMMUNICATOR. Write to the client, not the court.
Schema: {"hindi_letter": str, "english_letter": str, "next_visit_checklist": [str]}
Letters: warm, simple, under 180 words each, 6th-grade reading level, say exactly what happens
next and what to bring. Hindi in Devanagari."""),
}

_SYNTH = """You are the SENIOR COUNSEL chairing a legal-aid clinic review council in Madhya Pradesh.
Five specialists have reviewed one case. Write the counsel brief the supervising advocate reads
in two minutes before meeting the client. Markdown, under 600 words, these headings exactly:
## Verdict (2 lines: is the draft file-ready, and the single biggest gap)
## Evidence to collect (bullets, blocking items first, bold them)
## What the other side will say (top 3, each with our one-line answer)
## Plan (numbered, with day numbers and owner)
## Risks (bullets)
## Say to the client (3 plain sentences in English, then the same in Hindi)
Never invent facts; keep [TO CONFIRM] where the packet has it. Procedure only, no legal advice."""


def case_packet(case: dict) -> str:
    facts = case.get("facts_json") or "{}"
    sections = case.get("sections_json") or "[]"
    return (f"TODAY: {date.today().isoformat()}\nMODULE: {case.get('module')}\n"
            f"CLIENT: {case.get('client_name')}\nURGENCY: {case.get('urgency')}\n"
            f"LIMITATION DEADLINE: {case.get('deadline') or '[TO CONFIRM]'}\n"
            f"ELIGIBLE FOR FREE AID: {bool(case.get('eligible_aid'))} ({case.get('eligibility_reason') or ''})\n"
            f"SUMMARY: {case.get('summary')}\n\nFACTS JSON:\n{facts}\n\nSECTIONS JSON:\n{sections}\n\n"
            f"DRAFT:\n{case.get('draft_md') or '[no draft]'}")


def run_specialist(name: str, packet: str) -> dict:
    model, system = SPECIALISTS[name]
    return client.ask(model, system, packet, json_mode=True)


def synthesise(packet: str, agents: dict) -> str:
    user = packet + "\n\nSPECIALIST REPORTS:\n" + json.dumps(agents, ensure_ascii=False, indent=1)
    return client.ask(OPUS, _SYNTH, user)


def run_council(case: dict, on_agent_done=None) -> dict:
    """Run all specialists in parallel, then synthesise. on_agent_done(name, ok, ms) is
    called from the main thread as each finishes (for progress UI)."""
    t0 = time.time()
    packet = case_packet(case)
    agents, errors = {}, {}
    with ThreadPoolExecutor(max_workers=len(SPECIALISTS)) as pool:
        futs = {pool.submit(run_specialist, n, packet): n for n in SPECIALISTS}
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                agents[name] = fut.result()
                ok = True
            except Exception as e:  # one failed specialist must not sink the council
                errors[name] = str(e)[:300]
                ok = False
            if on_agent_done:
                on_agent_done(name, ok, int((time.time() - t0) * 1000))
    brief = synthesise(packet, agents) if agents else "_Council could not run: every specialist failed._"
    if on_agent_done:
        on_agent_done("synthesis", True, int((time.time() - t0) * 1000))
    return {"agents": agents, "errors": errors, "brief_md": brief,
            "ms": int((time.time() - t0) * 1000), "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S")}


def council_for_case(case_id: int, force: bool = False, on_agent_done=None) -> dict:
    """Load-or-run: stored council_json wins unless force. Persists the result."""
    from db import db
    case = db.get_case(case_id) or {}
    if not force and case.get("council_json"):
        return json.loads(case["council_json"])
    out = run_council(case, on_agent_done)
    db.update_case(case_id, council_json=json.dumps(out, ensure_ascii=False))
    return out
