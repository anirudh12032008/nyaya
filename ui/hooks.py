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
