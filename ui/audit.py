"""Audit trail widget for the case detail view (rendered in the case file's Audit tab)."""
import pandas as pd
import streamlit as st

from agent import audit as audit_mod
from ui import theme


def render_audit(case: dict) -> None:
    case_id = case["id"]
    audit = audit_mod.build_audit(case_id)

    with theme.card("Audit trail", "What a funder or a supervising advocate would ask for."):
        st.write(audit.get("plain_summary") or "")
        if st.button("Build audit PDF", key=f"audit_build{case_id}"):
            st.session_state[f"audit_pdf{case_id}"] = str(audit_mod.export_audit_pdf(case_id))
        path = st.session_state.get(f"audit_pdf{case_id}")
        if path:
            with open(path, "rb") as fh:
                st.download_button("Download audit PDF", fh.read(),
                                   file_name=f"case-{case_id}-audit.pdf",
                                   mime="application/pdf", key=f"audit_dl{case_id}",
                                   type="primary")

    theme.section("Timeline", "Every step this case went through")
    st.dataframe(pd.DataFrame(audit["timeline"] or [{"ts": "", "type": "", "detail": ""}]),
                 use_container_width=True, hide_index=True,
                 column_config={"ts": st.column_config.TextColumn("When", width="small"),
                                "type": st.column_config.TextColumn("Step", width="small"),
                                "detail": st.column_config.TextColumn("Detail", width="large")})

    theme.section("Model calls", "Which model did what, and whether the answer was cached")
    st.dataframe(pd.DataFrame(audit["model_calls"]
                              or [{"step": "", "model": "", "ms": 0, "cached": False}]),
                 use_container_width=True, hide_index=True,
                 column_config={"step": st.column_config.TextColumn("Step", width="medium"),
                                "model": st.column_config.TextColumn("Model", width="medium"),
                                "ms": st.column_config.NumberColumn("Milliseconds", width="small"),
                                "cached": st.column_config.CheckboxColumn("Cached", width="small")})
