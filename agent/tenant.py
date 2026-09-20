"""Stage 2: tenancy agreement review + counter-notice drafter.

A pure-Python pre-flagger catches the three clauses we know how to spot without
the model; the model adds the rest and writes the notice. Both are then filtered
against tenancy_rules.json so nothing invented survives.
"""
from __future__ import annotations

import io
import json
import re
from datetime import date

from agent import client, prompts
from agent.data import load

_WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "do": 2, "teen": 3,
             "char": 4, "paanch": 5, "chhe": 6}
_MONTHS = re.compile(
    r"\b(\d{1,3}|" + "|".join(_WORD_NUM) + r")\s*[-\s]?\s*(?:months?|maheene?|mahine)\b", re.I)
_AMOUNT = re.compile(r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)\s*(lakhs?|lacs?|crores?)?", re.I)


def extract_pdf_text(file_bytes: bytes) -> str:
    """Agreement PDF -> plain text (pypdf; scanned PDFs yield little or nothing)."""
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join((p.extract_text() or "") for p in reader.pages).strip()


def _months(s: str) -> int | None:
    m = _MONTHS.search(s)
    if not m:
        return None
    tok = m.group(1)
    return int(tok) if tok.isdigit() else _WORD_NUM.get(tok.lower())


def _rupees(s: str) -> int | None:
    m = _AMOUNT.search(s)
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    if unit.startswith(("lakh", "lac")):
        n *= 100_000
    elif unit.startswith("crore"):
        n *= 10_000_000
    return int(n)


def _clauses(text: str) -> list[str]:
    """Paragraph / numbered-clause split; the flag quotes one of these whole."""
    parts: list[str] = []
    for para in re.split(r"\n\s*\n", text or ""):
        for chunk in re.split(r"(?=(?:^|[\s|])\d{1,2}\s*[.)]\s+[A-Z(])", para):
            chunk = re.sub(r"\s+", " ", chunk).strip()
            if chunk:
                parts.append(chunk)
    return parts


def _severity(rule_id: str, fallback: str) -> str:
    try:
        rules = load("tenancy_rules").get("rules", [])
    except (OSError, ValueError):
        return fallback
    return next((r.get("severity", fallback) for r in rules if r.get("id") == rule_id), fallback)


def heuristic_flags(text: str) -> list[dict]:
    """Regex pre-flagger for the clauses that do not need a model call."""
    low = (text or "").lower()
    registered = re.search(r"\bregistered\b|\bregistration\b|sub.?registrar", low) is not None
    flags: list[dict] = []

    def add(clause: str, issue: str, rule_id: str, sev: str):
        if not any(f["rule_id"] == rule_id for f in flags):
            flags.append({"clause": clause[:300].strip(), "issue": issue,
                          "rule_id": rule_id, "severity": _severity(rule_id, sev)})

    for c in _clauses(text):
        cl = c.lower()
        n = _months(cl)

        # REG-17: term over 11 months, or an 11-month term that auto-renews, never registered
        if n and re.search(r"term|tenancy|lease|period|rent(?:ed)? for|duration", cl):
            auto = re.search(r"renew|auto|extend|rollover|roll over", cl) is not None
            if not registered and (n > 11 or (n == 11 and auto)):
                add(c, f"Tenancy of {n} months"
                       + (" with automatic renewal, which takes the effective term past 11 months,"
                          if n == 11 else ",")
                       + " is not stated to be registered; an unregistered lease over 11 months is "
                         "inadmissible to prove its terms.", "REG-17", "high")

        # MTA-11: security deposit of 3 months' rent or more
        if re.search(r"deposit|security|advance", cl):
            mult = n if (n and n >= 3) else None
            if mult is None:
                dep, rent = _rupees(cl), _monthly_rent(text)
                if dep and rent and dep >= 3 * rent:
                    mult = round(dep / rent)
            if mult:
                add(c, f"Security deposit of about {mult} months' rent exceeds the two-month "
                       "residential cap of the Model Tenancy Act 2021.", "MTA-11", "high")

        # CA-74: penalty / forfeiture with a figure attached
        if re.search(r"penalt|forfeit|liquidated|fine of|damages of", cl) and _rupees(cl):
            add(c, "A pre-fixed penalty is recoverable only up to the loss actually proved; "
                   "s.74 Contract Act caps it at reasonable compensation.", "CA-74", "high")

        if re.search(r"lock.?in|lockin", cl):
            add(c, "Lock-in period binding only the tenant is one-sided and unenforceable as a "
                   "penalty to the extent it exceeds proved loss.", "LOCKIN", "medium")

        if re.search(r"electric|water|power supply|essential service", cl) and \
                re.search(r"cut|disconnect|discontinu|stop|withhold|band", cl):
            add(c, "Withholding electricity or water to force the tenant out is prohibited; "
                   "essential supplies may not be cut off.", "ESSENTIAL-SERVICES", "high")
    return flags


def _monthly_rent(text: str) -> int | None:
    for m in re.finditer(r"[^.\n]{0,120}\brent\b[^.\n]{0,120}", text or "", re.I):
        seg = m.group(0)
        if re.search(r"per month|monthly|p\.m\.|/month|prati maah|per mensem", seg, re.I):
            amt = _rupees(seg)
            if amt:
                return amt
    return None


def draft_tenant(agreement_text: str, facts: dict | None = None, today: str | None = None) -> dict:
    from agent.sections import filter_sections  # lazy: import order independence

    today = today or date.today().isoformat()
    facts = facts or {}
    try:
        rules = load("tenancy_rules").get("rules", [])
    except (OSError, ValueError):
        rules = []
    lean = [{"id": r["id"], "title": r.get("title", ""), "gist": r.get("gist", ""),
             "severity": r.get("severity", "medium")} for r in rules]

    user = (
        f"Today's date is {today}.\n\n"
        f"FACTS JSON:\n{json.dumps(facts, ensure_ascii=False, indent=1)}\n\n"
        f"AGREEMENT TEXT / CLIENT'S WORDS:\n{agreement_text}\n\n"
        f"RULES (cite only these ids):\n{json.dumps(lean, ensure_ascii=False, indent=1)}"
    )
    out = client.ask(client.SONNET, prompts.load("draft_tenant"), user,
                     json_mode=True, temperature=0.3)
    out = out if isinstance(out, dict) else {}

    merged = list(heuristic_flags(agreement_text))
    seen = {f["rule_id"] for f in merged}
    for f in out.get("flags") or []:
        if isinstance(f, dict) and f.get("rule_id") not in seen:
            seen.add(f.get("rule_id"))
            merged.append(f)

    kept_flags, dropped_flags = filter_sections("tenant", [{**f, "id": f.get("rule_id")}
                                                           for f in merged])
    kept_flags = [{k: v for k, v in f.items() if k != "id"} for f in kept_flags]
    kept_secs, dropped_secs = filter_sections("tenant", out.get("sections") or [])
    for f in kept_flags:  # every flagged rule is a cited rule
        if not any(s.get("id") == f["rule_id"] for s in kept_secs):
            kept_secs.append({"id": f["rule_id"], "why": f["issue"]})

    return {
        "flags": kept_flags,
        "draft_markdown": out.get("draft_markdown", ""),
        "sections": kept_secs,
        "sections_dropped": dropped_secs + dropped_flags,
        "next_steps": out.get("next_steps") or [],
        "hindi_summary": out.get("hindi_summary", ""),
        "deadline_iso": out.get("deadline_iso") or None,
    }
