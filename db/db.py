"""SQLite store for the clinic workspace: cases, volunteers, feedback, events.

One module-level connection (check_same_thread=False) because Streamlit reruns
on its own threads. DB file is db/nyaya.db, overridable with $NYAYA_DB.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("NYAYA_DB") or ROOT / "db" / "nyaya.db")
SCHEMA = ROOT / "db" / "schema.sql"
SEED_CASES = ROOT / "data" / "seed_cases.json"

VOLUNTEERS = ["Adv. Priya Sharma", "Adv. Rahul Verma",
              "Meera Joshi (NLIU intern)", "Arjun Tiwari (NLIU intern)"]

# a case stops costing a volunteer capacity once it is filed or closed
DONE = ("filed", "closed")

CASE_COLS = ["created_at", "module", "status", "urgency", "client_name", "summary",
             "draft_md", "sections_json", "deadline", "assigned_to", "eligible_aid",
             "eligibility_reason", "intake_seconds", "trace_json", "facts_json", "council_json"]

_conn: sqlite3.Connection | None = None


def connect() -> sqlite3.Connection:
    global _conn
    if _conn is None or Path(_conn.execute("PRAGMA database_list").fetchone()[2]) != DB_PATH:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def days_to_deadline(deadline_iso: str | None) -> int | None:
    """Whole days from today to an ISO date. None if absent/unparseable."""
    if not deadline_iso:
        return None
    try:
        return (date.fromisoformat(str(deadline_iso)[:10]) - date.today()).days
    except ValueError:
        return None


def _wait_for_seed(timeout_s: int = 600) -> bool:
    """The DATA agent writes seed_cases.json concurrently; give it time."""
    deadline = time.time() + timeout_s
    while not SEED_CASES.exists() and time.time() < deadline:
        time.sleep(30)
    return SEED_CASES.exists()


def init() -> None:
    c = connect()
    c.executescript(SCHEMA.read_text())
    if "council_json" not in {r[1] for r in c.execute("PRAGMA table_info(cases)")}:
        c.execute("ALTER TABLE cases ADD COLUMN council_json TEXT")  # orchestra, added post-seed
    if not c.execute("SELECT 1 FROM volunteers LIMIT 1").fetchone():
        c.executemany("INSERT INTO volunteers(name, load) VALUES (?, 0)",
                      [(n,) for n in VOLUNTEERS])
    if not c.execute("SELECT 1 FROM cases LIMIT 1").fetchone() and _wait_for_seed():
        for row in json.loads(SEED_CASES.read_text()):
            create_case(row)
        recompute_loads()
    c.commit()


def recompute_loads() -> None:
    c = connect()
    c.execute("UPDATE volunteers SET load = (SELECT COUNT(*) FROM cases "
              "WHERE cases.assigned_to = volunteers.id "
              "AND COALESCE(cases.status,'new') NOT IN (?, ?))", DONE)
    c.commit()


def volunteers() -> list[dict]:
    return [dict(r) for r in connect().execute(
        "SELECT * FROM volunteers ORDER BY id").fetchall()]


def _lowest_load_volunteer() -> int | None:
    r = connect().execute("SELECT id FROM volunteers ORDER BY load, id LIMIT 1").fetchone()
    return r["id"] if r else None


def log_event(case_id: int, type: str, payload=None) -> None:
    c = connect()
    c.execute("INSERT INTO events(case_id, type, payload, ts) VALUES (?,?,?,?)",
              (case_id, type, json.dumps(payload, ensure_ascii=False, default=str)
               if payload is not None else None, _now()))
    c.commit()


def create_case(d: dict) -> int:
    d = dict(d)
    d.setdefault("created_at", _now())
    d.setdefault("status", "new")
    for k in ("sections_json", "trace_json", "facts_json", "council_json"):
        if not isinstance(d.get(k), (str, type(None))):
            d[k] = json.dumps(d[k], ensure_ascii=False, default=str)
    if not d.get("assigned_to"):
        d["assigned_to"] = _lowest_load_volunteer()

    c = connect()
    cols = [k for k in CASE_COLS if k in d]
    cur = c.execute(f"INSERT INTO cases({','.join(cols)}) "
                    f"VALUES({','.join('?' * len(cols))})", [d[k] for k in cols])
    case_id = cur.lastrowid
    if d.get("assigned_to") and d.get("status") not in DONE:
        c.execute("UPDATE volunteers SET load = load + 1 WHERE id = ?", (d["assigned_to"],))
    c.commit()
    log_event(case_id, "created", {"module": d.get("module"), "urgency": d.get("urgency"),
                                   "assigned_to": d.get("assigned_to")})
    return case_id


def get_case(id: int) -> dict | None:
    r = connect().execute("SELECT * FROM cases WHERE id = ?", (id,)).fetchone()
    return dict(r) if r else None


def list_cases(status=None, module=None, urgency=None) -> list[dict]:
    where, args = [], []
    for col, val in (("status", status), ("module", module), ("urgency", urgency)):
        if val:
            vals = [val] if isinstance(val, str) else list(val)
            if not vals:
                continue
            where.append(f"{col} IN ({','.join('?' * len(vals))})")
            args += vals
    sql = "SELECT * FROM cases" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id"
    return [dict(r) for r in connect().execute(sql, args).fetchall()]


def update_case(id: int, **fields) -> None:
    old = get_case(id)
    if not old or not fields:
        return
    for k in ("sections_json", "trace_json", "facts_json"):
        if k in fields and not isinstance(fields[k], (str, type(None))):
            fields[k] = json.dumps(fields[k], ensure_ascii=False, default=str)
    c = connect()
    changed = {k: v for k, v in fields.items() if k in CASE_COLS and v != old.get(k)}
    if not changed:
        return

    was_active = (old.get("status") or "new") not in DONE
    new_status = changed.get("status", old.get("status") or "new")
    new_owner = changed.get("assigned_to", old.get("assigned_to"))

    # load = number of active cases held, so adjust on close/file and on reassign
    if was_active and old.get("assigned_to") and (new_status in DONE or new_owner != old.get("assigned_to")):
        c.execute("UPDATE volunteers SET load = MAX(load - 1, 0) WHERE id = ?",
                  (old["assigned_to"],))
    if new_status not in DONE and new_owner and (
            not was_active or new_owner != old.get("assigned_to")):
        c.execute("UPDATE volunteers SET load = load + 1 WHERE id = ?", (new_owner,))

    c.execute(f"UPDATE cases SET {','.join(k + '=?' for k in changed)} WHERE id = ?",
              list(changed.values()) + [id])
    c.commit()
    log_event(id, "updated", changed)


def add_feedback(case_id: int, rating: str, note: str = "") -> int:
    c = connect()
    cur = c.execute("INSERT INTO feedback(case_id, rating, note, created_at) VALUES (?,?,?,?)",
                    (case_id, rating, note, _now()))
    c.commit()
    log_event(case_id, "feedback", {"rating": rating, "note": note})
    return cur.lastrowid


def list_feedback(case_id=None) -> list[dict]:
    c = connect()
    rows = (c.execute("SELECT * FROM feedback WHERE case_id = ? ORDER BY id", (case_id,))
            if case_id else c.execute("SELECT * FROM feedback ORDER BY id")).fetchall()
    return [dict(r) for r in rows]


def list_events(case_id: int) -> list[dict]:
    return [dict(r) for r in connect().execute(
        "SELECT * FROM events WHERE case_id = ? ORDER BY id", (case_id,)).fetchall()]


def _counts(sql: str) -> dict:
    return {(r[0] or "unknown"): r[1] for r in connect().execute(sql).fetchall()}


def stats() -> dict:
    c = connect()
    fb = _counts("SELECT rating, COUNT(*) FROM feedback GROUP BY rating")
    return {
        "total": c.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
        "per_module": _counts("SELECT module, COUNT(*) FROM cases GROUP BY module"),
        "per_status": _counts("SELECT status, COUNT(*) FROM cases GROUP BY status"),
        "per_volunteer": _counts(
            "SELECT v.name, COUNT(c.id) FROM volunteers v "
            "LEFT JOIN cases c ON c.assigned_to = v.id GROUP BY v.id"),
        "avg_intake_seconds": c.execute(
            "SELECT AVG(intake_seconds) FROM cases WHERE intake_seconds IS NOT NULL"
        ).fetchone()[0] or 0.0,
        "feedback_up": fb.get("up", 0) or fb.get("👍", 0),
        "feedback_down": fb.get("down", 0) or fb.get("👎", 0),
    }
