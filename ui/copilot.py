"""Volunteer copilot panel: the phone script, the next three actions, and the outcome form."""
import pandas as pd
import streamlit as st

from agent.copilot import plan
from db import db
from ui import theme

OUTCOMES = ["", *db.OUTCOMES]
OUTCOME_TONE = {"won": "ok", "settled": "ok", "lost": "danger", "withdrawn": "muted"}


def render_copilot(case: dict) -> None:
    if not case:
        return
    cid = case["id"]
    stored = case.get("copilot_json")

    with theme.card("Volunteer copilot",
                    "Opus reads the case, the council brief and similar past cases (~20s)."):
        c1, c2 = st.columns([1, 3])
        run = c1.button("Plan next steps" if not stored else "Re-plan", key=f"copilot{cid}",
                        type="primary" if not stored else "secondary", use_container_width=True)
        if stored:
            c2.caption("A plan is already on file — re-plan after anything changes.")

    out = None
    if run:
        with st.spinner("Opus is planning the call…"):
            try:
                out = plan(case, force=bool(stored))
            except RuntimeError as e:
                st.error(f"Copilot failed: {e}")
    elif stored:
        out = plan(case)  # cached, no API call

    if out:
        st.caption(f"Planned {out.get('ran_at', '')} · {out.get('ms', 0) / 1000:.0f}s")
        theme.section("Say this on the phone", "फ़ोन पर यही कहें")
        st.code(out.get("call_script") or "_empty_", language=None)
        if out.get("next_actions"):
            theme.section("Next actions", "Who does what, by when")
            st.dataframe(
                pd.DataFrame(out["next_actions"])[["action", "by_when", "why"]],
                use_container_width=True, hide_index=True,
                column_config={"action": st.column_config.TextColumn("Action", width="medium"),
                               "by_when": st.column_config.TextColumn("By when", width="small"),
                               "why": st.column_config.TextColumn("Why", width="large")})
        risks = out.get("risks") or []
        if risks:
            with theme.card("Risks to watch", "जोखिम"):
                for r in risks:
                    st.markdown(f"- ⚠️ {r}")

    _outcome_form(case)


def _outcome_form(case: dict) -> None:
    cid = case["id"]
    if case.get("outcome"):
        theme.section("Outcome", "परिणाम")
        theme.badges(theme.badge(case["outcome"], OUTCOME_TONE.get(case["outcome"], "info"),
                                 solid=True),
                     theme.badge(f"recorded {case.get('outcome_at') or ''}", "muted"))
        if case.get("outcome_note"):
            theme.quote(case["outcome_note"])

    with theme.card("Record the outcome",
                    "This is what the clinic learns from — write it when the matter ends."):
        with st.form(f"outcome{cid}"):
            current = case.get("outcome") or ""
            choice = st.selectbox("How did this case end?", OUTCOMES,
                                  index=OUTCOMES.index(current) if current in OUTCOMES else 0,
                                  format_func=lambda o: o or "— not yet —")
            note = st.text_area("What worked (this is what the clinic learns from)",
                                value=case.get("outcome_note") or "")
            if st.form_submit_button("Save outcome", type="primary"):
                db.set_outcome(cid, choice or None, note)
                st.rerun()
