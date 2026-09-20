"""Feedback -> prompt hints: what advocates keep correcting becomes a `## Learned` section."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from db import db

PROMPTS = Path(__file__).resolve().parent / "prompts"
HEADING = "## Learned"
# ratings the UI / seed data may use for a thumbs-down
NEGATIVE = {"down", "-1", "👎", "thumbs_down", "bad"}


def _is_negative(rating) -> bool:
    return str(rating).strip().lower() in NEGATIVE


def _key(note: str) -> str:
    """Collapse whitespace/case/punctuation so the same complaint counts as one."""
    return re.sub(r"[^\w\s]", "", " ".join(str(note).split())).strip().lower()


def corrections(module: str) -> list[dict]:
    """Every feedback note on cases of this module, most-corrected first."""
    case_ids = {c["id"] for c in db.list_cases(module=module)}
    notes = [f for f in db.list_feedback()
             if f["case_id"] in case_ids and (f.get("note") or "").strip()]
    total, down, first = Counter(), Counter(), {}
    for f in notes:
        k = _key(f["note"])
        total[k] += 1
        down[k] += _is_negative(f.get("rating"))
        first.setdefault(k, f["note"].strip())
    # thumbs-down count dominates, then raw frequency; ties keep insertion order
    return [{"note": first[k], "count": total[k], "down": down[k]}
            for k in sorted(total, key=lambda k: (-down[k], -total[k], list(first).index(k)))]


def top_corrections(module: str, n: int = 3) -> list[str]:
    return [c["note"] for c in corrections(module)[:n]]


def prompt_path(module: str) -> Path:
    return PROMPTS / f"draft_{module}.md"


def apply_hints(module: str, n: int = 3) -> tuple[str, str]:
    """Replace (not append to) the `## Learned` section with the top corrections.

    Returns (old_prompt, new_prompt) and writes the new one. Idempotent: running it
    twice with the same feedback produces the same file.
    """
    p = prompt_path(module)
    old = p.read_text(encoding="utf-8")
    body = old.split("\n" + HEADING)[0].rstrip()
    hints = top_corrections(module, n)
    new = body + "\n" if not hints else (
        body + "\n\n" + HEADING + "\n"
        "Corrections supervising advocates made on past drafts of this module — apply them:\n"
        + "".join(f"- {h}\n" for h in hints))
    if new != old:
        p.write_text(new, encoding="utf-8")
    return old, new
