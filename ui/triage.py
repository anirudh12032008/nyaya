"""Stage 5A/5C admin widgets: overnight triage brief + deadline sentinel."""
from datetime import date

import streamlit as st

from agent import sentinel, triage
from pdf.render import draft_to_pdf
from ui import theme


def render_triage_button() -> None:
    # ui/hooks.admin_extras already prints the section heading, so the card carries only the gloss
    with theme.card(caption="Classifies every new case and writes the morning brief · रात्रि छँटाई"):
        if st.button("Run overnight triage", type="primary"):
            with st.spinner("Classifying new cases and writing the morning brief..."):
                st.session_state["triage_result"] = triage.run_overnight()

    result = st.session_state.get("triage_result")
    if not result:
        return

    theme.stat_cards([
        {"label": "Cases triaged", "value": result["triaged"]},
        {"label": "Took", "value": f"{result['seconds']}s"},
    ])
    st.write("")
    theme.document(result["brief_md"])
    st.download_button(
        "Download brief PDF",
        data=draft_to_pdf(result["brief_md"],
                          {"forum": f"Morning brief - {date.today().isoformat()}"}),
        file_name=f"nyaya-brief-{date.today().isoformat()}.pdf",
        mime="application/pdf",
    )


def render_sentinel() -> None:
    with theme.card(caption="Move the clock to see which limitation periods bite · समय-सीमा प्रहरी"):
        a, b, c = st.columns([1, 1, 2])
        if a.button("Advance clock 30 days", use_container_width=True):
            sentinel.advance_clock(30)
        if b.button("Reset clock", use_container_width=True):
            sentinel.reset_clock()
        offset = sentinel.offset_days()
        c.metric("Simulated date", sentinel.today().strftime("%d-%m-%Y"),
                 f"+{offset} days" if offset else "real time")

    pending = sentinel.pending_notifications()
    if not pending:
        theme.empty_state("✅", "No deadline notifications pending",
                          "Nothing is close enough to its limitation date to warn about.")
        return

    theme.section("Pending notifications", f"{len(pending)} client(s) to warn")
    for n in pending:
        with st.container(border=True):
            left, right = st.columns([3, 1])
            left.markdown(f"**#{n['case_id']} · {n['client']}** — limitation {n['deadline']}")
            with right:
                theme.badges(theme.deadline_badge(n["days_left"]))
            st.code(n["message"], language=None)
