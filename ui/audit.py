"""Audit trail widget for the case detail view (wired from ui/hooks.py)."""
import pandas as pd
import streamlit as st

from agent import audit as audit_mod


def render_audit(case: dict) -> None:
    case_id = case["id"]
    with st.expander("Audit trail"):
        audit = audit_mod.build_audit(case_id)
        st.caption(audit.get("plain_summary") or "")

        st.markdown("**Timeline**")
        st.dataframe(pd.DataFrame(audit["timeline"] or [{"ts": "", "type": "", "detail": ""}]),
                     use_container_width=True, hide_index=True)

        st.markdown("**Model calls**")
        st.dataframe(pd.DataFrame(audit["model_calls"]
                                  or [{"step": "", "model": "", "ms": 0, "cached": False}]),
                     use_container_width=True, hide_index=True)

        if st.button("Build audit PDF", key=f"audit_build{case_id}"):
            st.session_state[f"audit_pdf{case_id}"] = str(audit_mod.export_audit_pdf(case_id))
        path = st.session_state.get(f"audit_pdf{case_id}")
        if path:
            with open(path, "rb") as fh:
                st.download_button("Download audit PDF", fh.read(),
                                   file_name=f"case-{case_id}-audit.pdf",
                                   mime="application/pdf", key=f"audit_dl{case_id}")
