"""Case queue + detail view for clinic volunteers."""
import json

import pandas as pd
import streamlit as st

from db import db
from ui import theme

STATUSES = ["new", "in_progress", "filed", "closed"]
MODULES = ["consumer", "police", "tenant", "labour", "other"]
URGENCIES = ["high", "medium", "low"]

URGENCY_TONE = {"high": "danger", "medium": "warn", "low": "muted"}
STATUS_TONE = {"new": "info", "in_progress": "accent", "filed": "ok", "closed": "muted"}


def _volunteer_names():
    return {v["id"]: v["name"] for v in db.volunteers()}


def _open(case_id: int) -> None:
    st.query_params["case"] = str(case_id)
    st.rerun()


def render():
    qp_case = st.query_params.get("case")
    if qp_case:
        try:
            return _detail(int(qp_case))
        except ValueError:
            st.error(f"Bad case id in URL: {qp_case}")

    theme.page_header("Case queue", "Every matter the clinic is carrying, newest last.",
                      hindi="मुकदमा सूची", eyebrow="Workspace")

    all_cases = db.list_cases()
    due_soon = [c for c in all_cases
                if (d := db.days_to_deadline(c.get("deadline"))) is not None and d < 30]
    theme.stat_cards([
        {"label": "Cases in queue", "value": len(all_cases)},
        {"label": "High urgency", "value": sum(1 for c in all_cases if c.get("urgency") == "high"),
         "delta": "needs a volunteer today", "tone": "danger"},
        {"label": "Limitation within 30 days", "value": len(due_soon),
         "delta": "file or seek condonation", "tone": "warn"},
        {"label": "Unassigned", "value": sum(1 for c in all_cases if not c.get("assigned_to")),
         "delta": "no volunteer yet", "tone": "muted"},
    ])
    st.write("")

    with theme.card("Filters", "Leave a filter empty to include everything."):
        c1, c2, c3 = st.columns(3)
        status = c1.multiselect("Status", STATUSES)
        module = c2.multiselect("Module", MODULES)
        urgency = c3.multiselect("Urgency", URGENCIES)

    cases = db.list_cases(status=status or None, module=module or None, urgency=urgency or None)
    if not cases:
        theme.empty_state("🗂️", "No cases match these filters",
                          "Clear a filter, or take a new matter through Intake.")
        return

    names = _volunteer_names()
    rows = []
    for c in cases:
        days = db.days_to_deadline(c.get("deadline"))
        rows.append({"id": c["id"], "client": c.get("client_name"), "module": c.get("module"),
                     "urgency": c.get("urgency"), "status": c.get("status"),
                     "volunteer": names.get(c.get("assigned_to"), "—"),
                     "deadline": c.get("deadline"), "days_left": days})

    _urgent_strip(cases, names)

    theme.section("All cases", f"{len(rows)} shown · समस्त मुकदमे")
    st.dataframe(
        pd.DataFrame(rows), use_container_width=True, hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "client": st.column_config.TextColumn("Client", width="medium"),
            "module": st.column_config.TextColumn("Module", width="small"),
            "urgency": st.column_config.TextColumn("Urgency", width="small"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "volunteer": st.column_config.TextColumn("Volunteer", width="medium"),
            "deadline": st.column_config.TextColumn("Limitation date", width="small"),
            "days_left": st.column_config.NumberColumn("Days left", width="small",
                                                       help="Negative means limitation has passed"),
        })

    c1, c2 = st.columns([3, 1])
    chosen = c1.selectbox(
        "Open case", [c["id"] for c in cases],
        format_func=lambda i: f"#{i} · {next(c['client_name'] for c in cases if c['id'] == i)}")
    c2.write("")
    if c2.button("Open case file", type="primary", use_container_width=True) and chosen:
        _open(chosen)


def _urgent_strip(cases: list[dict], names: dict) -> None:
    """The handful of cases whose limitation period is closest — clickable."""
    dated = [(db.days_to_deadline(c.get("deadline")), c) for c in cases]
    urgent = sorted(((d, c) for d, c in dated if d is not None and d < 30), key=lambda t: t[0])[:4]
    if not urgent:
        return

    theme.section("Closest to limitation", "Open these first · सबसे पहले ये देखें")
    for col, (days, c) in zip(st.columns(len(urgent)), urgent):
        with col, st.container(border=True):
            st.markdown(f"**{c.get('client_name') or 'Unnamed client'}**")
            st.caption(f"#{c['id']} · {names.get(c.get('assigned_to'), 'unassigned')}")
            theme.badges(theme.badge(c.get("module") or "other", "info"),
                         theme.deadline_badge(days))
            if st.button("Open", key=f"urg{c['id']}", use_container_width=True):
                _open(c["id"])


def _detail(case_id: int):
    case = db.get_case(case_id)
    if not case:
        st.error(f"Case #{case_id} not found.")
        return

    names = _volunteer_names()
    days = db.days_to_deadline(case.get("deadline"))
    theme.page_header(f"{case.get('client_name') or 'Unnamed client'}",
                      f"Limitation date {case.get('deadline') or 'not recorded'}",
                      hindi="मुकदमा फ़ाइल", eyebrow=f"Case file #{case_id}")

    theme.badges(theme.badge(case.get("module") or "other", "info"),
                 theme.badge(f"urgency {case.get('urgency') or 'unknown'}",
                             URGENCY_TONE.get(case.get("urgency"), "muted")),
                 theme.badge(case.get("status") or "new",
                             STATUS_TONE.get(case.get("status"), "muted")),
                 theme.badge(names.get(case.get("assigned_to"), "unassigned"), "muted"),
                 theme.deadline_badge(days))
    st.write("")

    _header_actions(case, names)
    _eligibility(case)

    tabs = st.tabs(["Draft", "Evidence", "Council", "Copilot", "Audit & history", "Feedback"])
    with tabs[0]:
        _draft_tab(case)
    with tabs[1]:
        from ui.evidence import render_evidence
        render_evidence(case)
    with tabs[2]:
        from ui.orchestra import render_council
        render_council(case)
    with tabs[3]:
        from ui.copilot import render_copilot
        render_copilot(case)
    with tabs[4]:
        _audit_tab(case)
    with tabs[5]:
        _feedback_tab(case)


def _header_actions(case: dict, names: dict) -> None:
    case_id = case["id"]
    with theme.card():
        a, b, c = st.columns([1, 1, 2])
        if a.button("← Back to queue", key=f"back{case_id}", use_container_width=True):
            st.query_params.pop("case", None)
            st.rerun()
        if b.button("Mark filed", key=f"file{case_id}", type="primary",
                    disabled=case.get("status") == "filed", use_container_width=True):
            db.update_case(case_id, status="filed")
            st.rerun()
        ids = list(names)
        with c:
            d, e = st.columns([3, 1])
            new_owner = d.selectbox("Reassign to", ids,
                                    index=ids.index(case["assigned_to"])
                                    if case.get("assigned_to") in ids else 0,
                                    format_func=lambda i: names[i], key=f"owner{case_id}")
            e.write("")
            if e.button("Reassign", key=f"reassign{case_id}",
                        disabled=new_owner == case.get("assigned_to"), use_container_width=True):
                db.update_case(case_id, assigned_to=new_owner)
                st.rerun()


def _eligibility(case: dict) -> None:
    """Section 12 Legal Services Authorities Act verdict, in plain words."""
    reason = case.get("eligibility_reason") or "No reason recorded."
    if case.get("eligible_aid"):
        st.success(f"**Free legal aid: eligible** · निःशुल्क विधिक सहायता — {reason}")
    else:
        st.warning(f"**Free legal aid: not established** · पात्रता सिद्ध नहीं — {reason}")


def _draft_tab(case: dict) -> None:
    case_id = case["id"]
    from pdf.qr import qr_for_case                      # stage4: QR back to this case
    from pdf.render import draft_to_pdf
    from ui.stage4 import extra_case_actions as share_actions

    st.download_button("Download PDF",
                       draft_to_pdf(case.get("draft_md") or "",
                                    {"deadline_iso": case.get("deadline")},
                                    qr_png=qr_for_case(case_id)),
                       file_name=f"nyaya-case-{case_id}.pdf", mime="application/pdf",
                       key=f"pdf{case_id}", type="primary")
    theme.document(case.get("draft_md") or "No draft stored.")

    sections = _loads(case.get("sections_json"), [])
    if sections:
        theme.section("Sections relied on", "The law this draft stands on · आधार धाराएँ")
        st.dataframe(pd.DataFrame(sections), use_container_width=True, hide_index=True)

    st.divider()
    share_actions(case)


def _audit_tab(case: dict) -> None:
    from ui.audit import render_audit
    render_audit(case)

    case_id = case["id"]
    trace = _loads(case.get("trace_json"), [])
    if trace:
        theme.section("Agent trace",
                      f"Intake took {case.get('intake_seconds') or 0:.1f}s end to end.")
        st.dataframe(pd.DataFrame(trace), use_container_width=True, hide_index=True)

    theme.section("History", "Every change written to this file · इतिहास")
    events = db.list_events(case_id)
    if not events:
        theme.empty_state("🕰️", "Nothing recorded yet")
        return
    for e in events:
        st.markdown(theme.kv(f"{e['ts']} · {e['type']}", e["payload"] or ""),
                    unsafe_allow_html=True)


def _feedback_tab(case: dict) -> None:
    case_id = case["id"]
    with theme.card("Was this draft usable?",
                    "The advocate's correction is what the clinic learns from."):
        note = st.text_input("Note (what the advocate corrected)", key=f"note{case_id}")
        f1, f2, _ = st.columns([1, 1, 4])
        if f1.button("👍 Usable", key=f"up{case_id}", use_container_width=True):
            db.add_feedback(case_id, "up", note)
            st.rerun()
        if f2.button("👎 Needs work", key=f"down{case_id}", use_container_width=True):
            db.add_feedback(case_id, "down", note)
            st.rerun()

    entries = db.list_feedback(case_id)
    if not entries:
        theme.empty_state("💬", "No feedback yet", "Rate the draft once an advocate has read it.")
        return
    theme.section("Earlier feedback")
    for f in entries:
        theme.badges(theme.badge(f["rating"], "ok" if f["rating"] == "up" else "warn"),
                     theme.badge(f["created_at"], "muted"))
        if f["note"]:
            theme.quote(f["note"])


def _loads(raw, default):
    try:
        return json.loads(raw) if raw else default
    except (ValueError, TypeError):
        return default
