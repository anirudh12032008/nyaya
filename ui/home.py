"""Clinic command centre: the landing page volunteers open first each morning."""
from datetime import date, datetime

import streamlit as st

from db import db
from ui import theme

PIPELINE = [
    {"key": "intake", "title": "Understand", "desc": "Listen to the client's story"},
    {"key": "triage", "title": "Classify", "desc": "Module, urgency, limitation"},
    {"key": "evidence", "title": "Extract", "desc": "Read the papers they brought"},
    {"key": "eligibility", "title": "Check", "desc": "Free legal aid under s.12"},
    {"key": "draft", "title": "Prepare", "desc": "Notice, complaint, application"},
    {"key": "verify", "title": "Review", "desc": "Citations and gaps flagged"},
]

EXAMPLES = {
    "Consumer": "A shop sold me a phone that stopped working in a week and refuses to refund.",
    "Police": "The police station will not register my FIR about a theft.",
    "Tenant": "My landlord locked my room and kept my deposit without notice.",
    "Labour": "My factory has not paid three months of wages.",
}


def _greeting() -> str:
    h = datetime.now().hour
    return "Good morning" if h < 12 else ("Good afternoon" if h < 17 else "Good evening")


def _go_to_case(case_id: int) -> None:
    st.query_params["case"] = str(case_id)
    st.session_state["_nav"] = "Cases"
    st.rerun()


def _start_intake(text: str) -> None:
    st.session_state["intake_text_seed"] = text
    st.session_state["_nav"] = "New intake"
    st.rerun()


def _case_rows(cases: list[dict], names: dict, key: str) -> None:
    """One line per case: id · client · module · volunteer · deadline badge · open button."""
    if not cases:
        st.caption("Nothing here right now.")
        return
    for c in cases:
        left, right = st.columns([9, 1])
        days = db.days_to_deadline(c.get("deadline"))
        left.markdown(
            '<div class="ny-row">'
            + theme.badge(f"#{c['id']}", "info")
            + theme.kv("", c.get("client_name") or " - ")
            + theme.kv("·", c.get("module") or " - ")
            + theme.kv("·", names.get(c.get("assigned_to")) or "unassigned")
            + theme.deadline_badge(days)
            + "</div>",
            unsafe_allow_html=True,
        )
        if right.button("Open", key=f"open_{key}_{c['id']}"):
            _go_to_case(c["id"])


def render() -> None:
    cases = db.list_cases()
    names = {v["id"]: v["name"] for v in db.volunteers()}
    stats = db.stats()
    open_cases = [c for c in cases if (c.get("status") or "new") not in db.DONE]

    theme.page_header(
        f"{_greeting()}, clinic desk",
        "Turn problems into possibilities - intake, triage and drafting in one place.",
        hindi="कानून सभी के लिए है, सिर्फ जानकार लोगों के लिए नहीं।",
        eyebrow="Nyaya · Madhya Pradesh legal aid",
    )

    # ── quick intake ────────────────────────────────────────────────────────
    with theme.card("Start a new matter", "समस्या यहाँ लिखें - Type or paste what the client told you."):
        text = st.text_area("Client's problem", key="home_intake_text", height=120,
                            placeholder="e.g. The shop refuses to refund a defective phone…",
                            label_visibility="collapsed")
        row = st.columns([2, 1, 1, 1, 1])
        if row[0].button("Analyse →", type="primary", use_container_width=True):
            if text.strip():
                _start_intake(text.strip())
            else:
                st.warning("Write a line or two first, or pick an example.")
        for col, (label, sample) in zip(row[1:], EXAMPLES.items()):
            if col.button(label, key=f"eg_{label}", use_container_width=True):
                _start_intake(sample)

    # ── pipeline ────────────────────────────────────────────────────────────
    theme.section("Your case, our AI agents", "Every matter walks the same six steps.")
    theme.agent_strip(PIPELINE)
    st.write("")

    if not cases:
        theme.empty_state("📁", "No cases yet",
                          "Take the first intake above and the clinic queue will fill up here.")
        return

    # ── work queue ──────────────────────────────────────────────────────────
    theme.section("Work queue", "काम की सूची")
    urgent = [c for c in open_cases if c.get("urgency") == "high"]
    recent = sorted(cases, key=lambda c: c["id"], reverse=True)[:8]
    unassigned = [c for c in open_cases if not c.get("assigned_to")]
    t_urgent, t_recent, t_unassigned = st.tabs(
        [f"Urgent ({len(urgent)})", "Recent", f"Unassigned ({len(unassigned)})"])
    with t_urgent:
        _case_rows(urgent[:8], names, "urg")
    with t_recent:
        _case_rows(recent, names, "rec")
    with t_unassigned:
        _case_rows(unassigned[:8], names, "una")

    # ── deadlines + brief ───────────────────────────────────────────────────
    dated = sorted(((db.days_to_deadline(c.get("deadline")), c) for c in open_cases
                    if db.days_to_deadline(c.get("deadline")) is not None),
                   key=lambda p: p[0])
    today = date.today().isoformat()
    new_today = [c for c in cases if str(c.get("created_at") or "")[:10] == today]
    no_draft = [c for c in open_cases if not (c.get("draft_md") or "").strip()]
    near = [c for d, c in dated if d < 10]

    left, right = st.columns([1, 1])
    with left:
        with theme.card("Deadline watchlist", "Soonest limitation first"):
            if not dated:
                st.caption("No limitation dates recorded on open cases.")
            for days, c in dated[:6]:
                st.markdown(
                    '<div class="ny-row">'
                    + theme.badge(f"#{c['id']}", "danger" if days < 10 else "muted")
                    + theme.kv("", c.get("client_name") or " - ")
                    + theme.deadline_badge(days)
                    + "</div>", unsafe_allow_html=True)
    with right:
        with theme.card("Today's brief", "आज का सार"):
            st.markdown(
                f"- **{len(new_today)}** new case(s) opened today\n"
                f"- **{len(urgent)}** open case(s) marked high urgency\n"
                f"- **{len(no_draft)}** open case(s) still without a draft\n"
                f"- **{len(near)}** open case(s) inside 10 days of limitation"
            )
            if near:
                theme.quote(f"Nearest limitation: case #{near[0]['id']} - "
                            f"{near[0].get('client_name') or 'client'}.")

    # ── clinic impact ───────────────────────────────────────────────────────
    theme.section("Clinic impact", "Counted from the case file, not estimated.")
    per_status = stats.get("per_status", {})
    theme.stat_cards([
        {"label": "Cases on file", "value": stats.get("total", 0)},
        {"label": "New", "value": per_status.get("new", 0), "tone": "info"},
        {"label": "High urgency", "value": len(urgent), "tone": "danger"},
        {"label": "Eligible for aid",
         "value": sum(1 for c in cases if c.get("eligible_aid")), "tone": "ok"},
        {"label": "Volunteers holding cases",
         "value": sum(1 for v in db.volunteers() if (v.get("load") or 0) > 0), "tone": "accent"},
    ])
