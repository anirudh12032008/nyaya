"""Ask Nyaya: an agentic chatbot over the clinic workspace (Claude tool-use loop).

chat_turn(history, user_text, focus_case_id=None, on_tool=None) -> (reply_text, new_history)
history is the raw Anthropic messages list; keep it in session state and pass it back.
Tools let Claude read the queue, open cases, look up statute sections, compute the
consumer forum, find similar cases, run the review council and update case status.
"""
from __future__ import annotations

import json
from datetime import date

from agent import client, forum, sections
from db import db

MODEL = "claude-opus-5"

SYSTEM = """You are Nyaya, the assistant for a legal-aid clinic in Madhya Pradesh, India.
You talk to clinic volunteers and the supervising advocate. Today is {today}.
Use tools to look at real data before answering; never guess a case's contents. Be concise,
use bullets for lists, and answer in the language the user writes (Hindi, Hinglish or English).
You are not a lawyer: explain procedure, forums, fees, deadlines and what the clinic should do
next, and say when something needs the supervising advocate. Never invent facts; say
[TO CONFIRM] when the record lacks something. If a case has no council brief and the user asks
for strategy, evidence or risks, run the council first.{focus}"""

TOOLS = [
    {"name": "list_cases", "description": "List cases in the queue. All filters optional.",
     "input_schema": {"type": "object", "properties": {
         "status": {"type": "string", "enum": ["new", "in_progress", "filed", "closed"]},
         "module": {"type": "string", "enum": ["consumer", "police", "tenant", "labour", "other"]},
         "urgency": {"type": "string", "enum": ["high", "medium", "low"]}}}},
    {"name": "get_case", "description": "Full record of one case: facts, draft, sections, deadline, council brief.",
     "input_schema": {"type": "object", "properties": {"case_id": {"type": "integer"}},
                      "required": ["case_id"]}},
    {"name": "search_sections",
     "description": "Search the clinic's statute data (Consumer Protection Act rules, BNS sections, MP tenancy rules, labour law) by keyword.",
     "input_schema": {"type": "object", "properties": {
         "module": {"type": "string", "enum": ["consumer", "police", "tenant", "labour"]},
         "query": {"type": "string"}}, "required": ["module", "query"]}},
    {"name": "compute_forum",
     "description": "Consumer forum, court fee and limitation for a claim amount in rupees.",
     "input_schema": {"type": "object", "properties": {"amount_inr": {"type": "integer"}},
                      "required": ["amount_inr"]}},
    {"name": "similar_cases", "description": "Find past cases similar to a description.",
     "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}},
                      "required": ["summary"]}},
    {"name": "run_council",
     "description": "Run the five-agent review council on a case (evidence, opponent, strategy, risk, client letter) and return the counsel brief. Takes ~1 minute; reuses a stored brief unless force=true.",
     "input_schema": {"type": "object", "properties": {"case_id": {"type": "integer"},
                                                       "force": {"type": "boolean"}},
                      "required": ["case_id"]}},
    {"name": "export_audit",
     "description": "Build the funder/DLSA audit-trail PDF for a case (timeline, model calls, verification, council) and return its path plus a plain-English summary.",
     "input_schema": {"type": "object", "properties": {"case_id": {"type": "integer"}},
                      "required": ["case_id"]}},
    {"name": "update_case", "description": "Change a case's status or urgency. Only when the user asks.",
     "input_schema": {"type": "object", "properties": {
         "case_id": {"type": "integer"},
         "status": {"type": "string", "enum": ["new", "in_progress", "filed", "closed"]},
         "urgency": {"type": "string", "enum": ["high", "medium", "low"]}},
         "required": ["case_id"]}},
]


def _search_sections(module: str, query: str) -> list:
    q = query.lower().split()
    hits = []
    for e in sections.entries(module):
        blob = json.dumps(e, ensure_ascii=False).lower()
        score = sum(w in blob for w in q)
        if score:
            hits.append((score, e))
    return [e for _, e in sorted(hits, key=lambda x: -x[0])[:8]]


def dispatch(name: str, args: dict):
    """Run one tool. Returns JSON-serialisable data; raises on bad input."""
    if name == "list_cases":
        rows = db.list_cases(**{k: v for k, v in args.items() if v})
        return [{k: c.get(k) for k in ("id", "client_name", "module", "urgency", "status",
                                       "deadline", "summary")} for c in rows[:40]]
    if name == "get_case":
        c = db.get_case(int(args["case_id"]))
        if not c:
            return {"error": f"no case #{args['case_id']}"}
        c = dict(c)
        c["days_to_deadline"] = db.days_to_deadline(c.get("deadline"))
        if c.get("council_json"):
            c["council_brief_md"] = json.loads(c.pop("council_json")).get("brief_md")
        c.pop("trace_json", None)
        return c
    if name == "search_sections":
        return _search_sections(args["module"], args["query"])
    if name == "compute_forum":
        return forum.compute(int(args["amount_inr"]))
    if name == "similar_cases":
        from agent.similar import find_similar
        return find_similar(args["summary"], None)
    if name == "run_council":
        from agent.orchestra import council_for_case
        out = council_for_case(int(args["case_id"]), force=bool(args.get("force")))
        return {"brief_md": out["brief_md"], "errors": out.get("errors"), "ms": out["ms"]}
    if name == "export_audit":
        from agent.audit import build_audit, export_audit_pdf
        cid = int(args["case_id"])
        return {"pdf_path": str(export_audit_pdf(cid)),
                "plain_summary": build_audit(cid)["plain_summary"]}
    if name == "update_case":
        cid = int(args.pop("case_id"))
        db.update_case(cid, **{k: v for k, v in args.items() if v})
        return {"ok": True, "case": {k: db.get_case(cid).get(k) for k in ("id", "status", "urgency")}}
    raise ValueError(f"unknown tool {name}")


def _system(focus_case_id):
    focus = ""
    if focus_case_id:
        focus = (f"\nThe user currently has case #{focus_case_id} open; assume questions are "
                 f"about it unless they say otherwise, and call get_case on it first.")
    return SYSTEM.format(today=date.today().isoformat(), focus=focus)


def chat_turn(history: list, user_text: str, focus_case_id: int | None = None,
              on_tool=None, max_rounds: int = 8) -> tuple[str, list]:
    """One user turn, including any tool rounds. on_tool(name, args, result) reports each call."""
    api = client._get_client().with_options(timeout=600.0, max_retries=2)  # same key/.env, longer timeout
    history = list(history) + [{"role": "user", "content": user_text}]
    system = _system(focus_case_id)
    reply = ""
    for _ in range(max_rounds):
        with api.messages.stream(model=MODEL, max_tokens=16000, system=system, tools=TOOLS,
                                 output_config={"effort": "medium"}, messages=history) as s:
            resp = s.get_final_message()
        history.append({"role": "assistant", "content": [b.model_dump(exclude_none=True)
                                                         for b in resp.content]})
        reply = "".join(b.text for b in resp.content if b.type == "text")
        if resp.stop_reason != "tool_use":
            break
        results = []
        for b in resp.content:
            if b.type != "tool_use":
                continue
            try:
                out = dispatch(b.name, dict(b.input))
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": json.dumps(out, ensure_ascii=False, default=str)[:60000]})
            except Exception as e:
                out = {"error": str(e)[:300]}
                results.append({"type": "tool_result", "tool_use_id": b.id, "is_error": True,
                                "content": json.dumps(out)})
            if on_tool:
                on_tool(b.name, dict(b.input), out)
        history.append({"role": "user", "content": results})
    else:
        reply = reply or "_Stopped after too many tool rounds; ask again more narrowly._"
    return reply, history


if __name__ == "__main__":
    import sys
    print(chat_turn([], " ".join(sys.argv[1:]) or "Which cases are closest to their deadline?",
                    on_tool=lambda n, a, r: print(f"  [tool] {n}({a})"))[0])
