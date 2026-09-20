"""Intake -> workspace bridge. Stage 1 calls on_draft_complete(result)."""
import streamlit as st

from agent.case_service import persist_intake
from db import db


def on_draft_complete(result: dict) -> None:
    case_id = persist_intake(st.session_state.get("intake_text", ""), result)
    st.session_state["last_case_id"] = case_id
    case = db.get_case(case_id) or {}
    names = {v["id"]: v["name"] for v in db.volunteers()}
    who = names.get(case.get("assigned_to"), "unassigned")
    verdict = "eligible for free legal aid" if case.get("eligible_aid") else "not established"
    st.success(f"Case #{case_id} created, assigned to {who}. "
               f"Eligibility: {verdict} — {case.get('eligibility_reason') or ''}")


# Stage 4 / 5 extras, re-exported so cases.py / admin.py pick them up via getattr.
from ui.stage4 import extra_case_actions as _s4_case, admin_extras as _s4_admin  # noqa: E402


def extra_case_actions(case: dict) -> None:
    _s4_case(case)
    from ui.orchestra import render_council  # orchestra: five-agent council on demand
    st.divider(); render_council(case)


def admin_extras() -> None:
    _s4_admin()
    from ui.triage import render_triage_button, render_sentinel  # 5A / 5C
    st.divider(); st.subheader("Overnight triage"); render_triage_button()
    st.divider(); st.subheader("Deadline sentinel"); render_sentinel()
