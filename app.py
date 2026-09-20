"""Nyaya - Streamlit entry / page router."""
import streamlit as st

st.set_page_config(page_title="Nyaya", page_icon="⚖️", layout="wide")

from ui import intake, cases, admin  # noqa: E402  (each page exposes render())

PAGES = {"Intake": intake, "Cases": cases, "Admin": admin}

qp = st.query_params
default = "Cases" if qp.get("case") else "Intake"
choice = st.sidebar.radio("Nyaya", list(PAGES), index=list(PAGES).index(default))
st.sidebar.caption("Legal aid clinic agent · Madhya Pradesh")
PAGES[choice].render()
