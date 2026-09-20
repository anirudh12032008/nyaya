"""Stage 5A/5C admin widgets: overnight triage brief + deadline sentinel."""
from datetime import date

import streamlit as st

from agent import sentinel, triage
from pdf.render import draft_to_pdf


def render_triage_button() -> None:
    st.subheader("Overnight triage")
    if st.button("Run overnight triage", type="primary"):
        with st.spinner("Classifying new cases and writing the morning brief..."):
            st.session_state["triage_result"] = triage.run_overnight()

    result = st.session_state.get("triage_result")
    if not result:
        return

    st.caption(f"Triaged {result['triaged']} new case(s) in {result['seconds']}s")
    st.markdown(result["brief_md"])
    st.download_button(
        "Download brief PDF",
        data=draft_to_pdf(result["brief_md"],
                          {"forum": f"Morning brief - {date.today().isoformat()}"}),
        file_name=f"nyaya-brief-{date.today().isoformat()}.pdf",
        mime="application/pdf",
    )


def render_sentinel() -> None:
    st.subheader("Deadline sentinel")
    a, b, c = st.columns([1, 1, 2])
    if a.button("Advance clock 30 days"):
        sentinel.advance_clock(30)
    if b.button("Reset clock"):
        sentinel.reset_clock()
    offset = sentinel.offset_days()
    c.metric("Simulated date", sentinel.today().strftime("%d-%m-%Y"),
             f"+{offset} days" if offset else "real time")

    pending = sentinel.pending_notifications()
    st.caption(f"Pending notifications: {len(pending)}")
    for n in pending:
        with st.container(border=True):
            left, right = st.columns([3, 1])
            left.write(f"**#{n['case_id']} · {n['client']}** — limitation {n['deadline']}")
            days = n["days_left"]
            right.markdown(f":red-background[{-days} days overdue]" if days < 0
                           else f":orange-background[{days} days left]")
            st.code(n["message"], language=None)
