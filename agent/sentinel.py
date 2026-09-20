"""Stage 5C: deadline sentinel.

A simulated clock (an integer day offset in db/clock.json, overridable with
$NYAYA_CLOCK) lets the demo jump forward without touching any real date.
Reminder text is a Python template -- no model call, so it never drifts and
never costs a token.
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

from db import db

ROOT = Path(__file__).resolve().parent.parent
WINDOW_DAYS = 30
DONE = db.DONE  # filed/closed cases stop being chased


def _clock_path() -> Path:
    # read env per call: tests point NYAYA_CLOCK at a tmp file without reloading
    return Path(os.environ.get("NYAYA_CLOCK") or ROOT / "db" / "clock.json")


def offset_days() -> int:
    p = _clock_path()
    try:
        return int(json.loads(p.read_text()).get("offset_days", 0))
    except (OSError, ValueError, AttributeError):
        return 0


def _write(offset: int) -> date:
    p = _clock_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"offset_days": int(offset)}))
    return today()


def today() -> date:
    """Real today plus the simulated offset."""
    return date.today() + timedelta(days=offset_days())


def advance_clock(days: int = 30) -> date:
    """Move the simulated clock forward (cumulative). Returns the new date."""
    return _write(offset_days() + int(days))


def reset_clock() -> date:
    return _write(0)


def days_left(deadline_iso: str | None) -> int | None:
    if not deadline_iso:
        return None
    try:
        return (date.fromisoformat(str(deadline_iso)[:10]) - today()).days
    except ValueError:
        return None


def _message(client: str, module: str, case_id: int, deadline: date, days: int) -> str:
    dmy = deadline.strftime("%d-%m-%Y")
    head = f"Namaste {client} ji, aapke {module} case (#{case_id}) ki limitation {dmy} ko "
    tail = ("khatam ho chuki hai, turant advocate se milein."
            if days < 0 else
            f"khatam ho rahi hai ({days} din baaki).")
    return head + tail + " Kripya jald se jald clinic se sampark karein - NLIU Legal Aid Clinic, Bhopal."


def pending_notifications() -> list[dict]:
    """Open cases whose limitation falls inside the next 30 days, or has passed."""
    out = []
    for c in db.list_cases():
        if (c.get("status") or "new") in DONE:
            continue
        d = days_left(c.get("deadline"))
        if d is None or d > WINDOW_DAYS:
            continue
        deadline = date.fromisoformat(str(c["deadline"])[:10])
        client = c.get("client_name") or "[TO CONFIRM]"
        out.append({
            "case_id": c["id"],
            "client": client,
            "deadline": deadline.isoformat(),
            "days_left": d,
            "message": _message(client, c.get("module") or "legal", c["id"], deadline, d),
        })
    return sorted(out, key=lambda r: r["days_left"])
