"""Stage 5G: case-similarity memory. No vector DB — Sonnet just reads summaries.

find_similar(summary, facts, k=3) -> [{"case_id","client_name","module","why","what_worked"}]
Only case_ids that actually exist in the DB are kept; the model's "why" is trusted for
free text only, everything else (client_name, module, what_worked) is filled in from the
DB row in Python so the model can't fabricate a case that never happened.
"""
import json

from agent import client, prompts
from db import db as db_mod

WORKED = ("filed", "closed")


def find_similar(summary: str, facts: dict | None, k: int = 3) -> list[dict]:
    cases = db_mod.list_cases()[:20]
    if not cases or not (summary or "").strip():
        return []

    by_id = {c["id"]: c for c in cases}
    slim = [{"id": c["id"], "module": c.get("module"), "summary": c.get("summary"),
             "status": c.get("status")} for c in cases]

    template = prompts.load("similar")
    sys_prompt = (template
                  .replace("{k}", str(k))
                  .replace("{summary}", summary)
                  .replace("{facts}", json.dumps(facts or {}, ensure_ascii=False))
                  .replace("{cases}", json.dumps(slim, ensure_ascii=False)))
    raw = client.ask(client.SONNET, sys_prompt,
                      "Which past cases are most similar, and what worked?",
                      json_mode=True, temperature=0)

    out = raw if isinstance(raw, dict) else {}
    result = []
    for entry in (out.get("similar") or [])[:k]:
        cid = entry.get("case_id") if isinstance(entry, dict) else entry
        try:
            cid = int(cid)
        except (TypeError, ValueError):
            continue
        row = by_id.get(cid)
        if row is None:  # guard: drop any id the model invented
            continue
        result.append({
            "case_id": cid,
            "client_name": row.get("client_name") or "",
            "module": row.get("module") or "",
            "why": (entry.get("why") if isinstance(entry, dict) else "") or "",
            "what_worked": "worked" if (row.get("status") in WORKED) else "in progress",
        })
    return result
