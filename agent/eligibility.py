"""Stage 3: NALSA s.12 eligibility screen (Haiku, temp 0, JSON)."""
from __future__ import annotations

import json

from agent import data, prompts
from agent.client import HAIKU, ask

NO_SIGNAL = "no category identified; ask client about income/category"


def _system() -> str:
    cfg = data.load("nalsa_eligibility")
    cats = [{"id": c["id"], "label": c["label"]} for c in cfg.get("categories", [])]
    ceiling = (cfg.get("income_ceiling_inr") or {}).get("mp", 300000)
    return prompts.load("eligibility").replace(
        "{categories}", json.dumps(cats, ensure_ascii=False, indent=1)
    ).replace("{ceiling}", str(ceiling))


def assess(facts: dict | None, summary: str = "") -> dict:
    """-> {"eligible", "category", "reason", "needs_info"}. Never raises."""
    user = ("CLIENT FACTS (JSON):\n"
            f"{json.dumps(facts or {}, ensure_ascii=False, default=str)}\n\n"
            f"CASE SUMMARY:\n{summary or ''}")
    try:
        r = ask(HAIKU, _system(), user, json_mode=True, temperature=0.0, max_tokens=512)
        if not isinstance(r, dict):
            raise ValueError("eligibility did not return an object")
        out = {"eligible": bool(r.get("eligible")),
               "category": str(r.get("category") or ""),
               "reason": str(r.get("reason") or "")}
    except Exception as e:  # no API key, timeout, bad JSON -> screen by hand
        out = {"eligible": False, "category": "",
               "reason": f"{NO_SIGNAL} (automatic screen unavailable: {type(e).__name__})"}
    out["needs_info"] = not out["eligible"] and not out["category"]
    return out
