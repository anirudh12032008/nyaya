"""Nyaya - Streamlit entry / page router."""
import streamlit as st

st.set_page_config(page_title="Nyaya", page_icon="⚖️", layout="wide")

from db.db import init as _db_init; _db_init()  # noqa: E402  (schema + seed, idempotent)
from ui import intake, cases, admin, chat, tour  # noqa: E402  (each page exposes render())

PAGES = {"Guided tour": tour, "Intake": intake, "Cases": cases,
         "Ask Nyaya": chat, "Admin": admin}

qp = st.query_params
if qp.get("clinic"):
    st.caption(f"Clinic: {qp['clinic']}")

page = qp.get("page", "")
if page.startswith("guide-"):                                   # stage4: public how-to page
    from ui import stage4
    stage4.render_guide(page[len("guide-"):])
elif qp.get("case") and qp.get("view") == "readonly":           # stage4: shared read-only case
    from ui import stage4
    stage4.render_readonly(qp["case"])
else:
    default = "Cases" if qp.get("case") else "Intake"
    choice = st.sidebar.radio("Nyaya", list(PAGES), index=list(PAGES).index(default))
    st.sidebar.caption("Legal aid clinic agent · Madhya Pradesh")
    PAGES[choice].render()
