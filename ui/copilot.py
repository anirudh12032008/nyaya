"""Volunteer copilot panel: the phone script, the next three actions, and the outcome form."""
import pandas as pd
import streamlit as st

from agent.copilot import plan
from db import db

OUTCOMES = ["", *db.OUTCOMES]


def render_copilot(case: dict) -> None:
    if not case:
        return
    cid = case["id"]
    st.subheader("Volunteer copilot")
    stored = case.get("copilot_json")
    c1, c2 = st.columns([1, 3])
    run = c1.button("Plan next steps" if not stored else "Re-plan", key=f"copilot{cid}",
                    type="primary" if not stored else "secondary")
    c2.caption("Opus reads the case, the council brief and similar past cases (~20s).")

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
        st.markdown("**Say this on the phone**")
        st.code(out.get("call_script") or "_empty_", language=None)
        if out.get("next_actions"):
            st.markdown("**Next actions**")
            st.dataframe(pd.DataFrame(out["next_actions"])[["action", "by_when", "why"]],
                         use_container_width=True, hide_index=True)
        for r in out.get("risks") or []:
            st.markdown(f"- ⚠️ {r}")

    _outcome_form(case)


def _outcome_form(case: dict) -> None:
    cid = case["id"]
    st.markdown("**Outcome**")
    if case.get("outcome"):
        st.caption(f"Recorded {case.get('outcome_at') or ''}: **{case['outcome']}** — "
                   f"{case.get('outcome_note') or ''}")
    with st.form(f"outcome{cid}"):
        current = case.get("outcome") or ""
        choice = st.selectbox("How did this case end?", OUTCOMES,
                              index=OUTCOMES.index(current) if current in OUTCOMES else 0,
                              format_func=lambda o: o or "— not yet —")
        note = st.text_area("What worked (this is what the clinic learns from)",
                            value=case.get("outcome_note") or "")
        if st.form_submit_button("Save outcome"):
            db.set_outcome(cid, choice or None, note)
            st.rerun()
