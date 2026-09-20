"""Stage 5B: a second Sonnet call reviews every draft; one automatic redraft on fail."""
from __future__ import annotations

import json
from datetime import date

from agent import client, prompts, sections as sec

TYPES = {"section", "forum", "placeholder", "unsupported_claim", "missing_part"}


def _slice(module: str, draft: dict) -> list[dict]:
    """id/title/gist for every id the draft cites, from the authoritative JSON."""
    by_norm = {sec.norm(e["id"]): e for e in sec.entries(module)}
    out = []
    for s in draft.get("sections") or []:
        e = by_norm.get(sec.norm((s.get("id") if isinstance(s, dict) else s) or ""))
        if e and e not in out:
            out.append({"id": e["id"], "title": e.get("title", ""), "gist": e.get("gist", "")})
    return out


def _lean(draft: dict) -> dict:
    keys = ("draft_markdown", "sp_letter_markdown", "demand_letter_markdown", "flags",
            "sections", "next_steps", "deadline_iso", "station_refused", "forum",
            "limitation")
    return {k: draft[k] for k in keys if draft.get(k) not in (None, "", [])}


def verify(module: str, facts: dict, forum: dict | None, draft: dict, raw_text: str = "",
           today: str | None = None) -> dict:
    """-> {"pass": bool, "issues": [...]}; never raises (API failure -> pass None + skipped)."""
    parts = [f"TODAY: {today or date.today().isoformat()}", f"MODULE: {module}",
             "FACTS (JSON):\n" + json.dumps(facts or {}, ensure_ascii=False, indent=1)]
    if raw_text:
        parts.append("CLIENT'S OWN WORDS:\n" + raw_text)
    if forum:
        parts.append("FORUM AND FEE, computed in Python (the draft must match):\n"
                     + json.dumps(forum, ensure_ascii=False, indent=1))
    parts += ["DRAFT (JSON):\n" + json.dumps(_lean(draft), ensure_ascii=False, indent=1),
              "SECTIONS JSON slice for every cited id:\n"
              + json.dumps(_slice(module, draft), ensure_ascii=False, indent=1)]
    try:
        raw = client.ask(client.SONNET, prompts.load("verify"), "\n\n".join(parts),
                         json_mode=True, temperature=0)
    except Exception as e:  # API down and nothing cached: the draft still ships
        return {"pass": None, "issues": [], "skipped": str(e)[:200]}
    if not isinstance(raw, dict) or not isinstance(raw.get("pass"), bool):
        return {"pass": None, "issues": [], "skipped": "verifier returned no pass/fail"}
    issues = [{"type": i.get("type") if i.get("type") in TYPES else "unsupported_claim",
               "detail": str(i.get("detail", "")), "fix": str(i.get("fix", ""))}
              for i in raw.get("issues") or [] if isinstance(i, dict)]
    return {"pass": raw["pass"] and not issues, "issues": issues}


def redraft_with_issues(module: str, facts: dict, forum: dict | None, draft: dict,
                        issues: list, today: str | None = None, raw_text: str = "") -> dict:
    """Rerun the module's drafter with the reviewer's issues injected. Section guard still runs."""
    today = today or date.today().isoformat()
    lines = [f"- [{i.get('type')}] {i.get('detail')} -> FIX: {i.get('fix')}" for i in issues]
    extra = ("## Reviewer issues to fix\nA senior advocate reviewed your previous draft and found "
             "these problems. Produce a corrected full draft that fixes every one of them; keep "
             "everything else unchanged.\n" + "\n".join(lines)
             + "\n\nPREVIOUS DRAFT (markdown):\n" + (draft.get("draft_markdown") or ""))
    if module == "consumer":
        from agent.draft import draft_consumer
        return draft_consumer(facts, forum or {}, today=today, extra=extra)
    if module == "police":
        from agent.police import draft_police
        return draft_police(facts, raw_text, today, extra=extra)
    if module == "tenant":
        from agent.tenant import draft_tenant
        return draft_tenant(raw_text, facts, today, extra=extra)
    if module == "labour":
        from agent.labour import draft_labour
        return draft_labour(facts, raw_text, today, extra=extra)
    raise ValueError(f"no drafter for module {module!r}")
