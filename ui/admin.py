"""Clinic head dashboard."""
import pandas as pd
import streamlit as st

from db import db


def render():
    st.title("Clinic dashboard")
    s = db.stats()
    new = s["per_status"].get("new", 0)
    urgent = len(db.list_cases(urgency="high"))

    m = st.columns(5)
    m[0].metric("Total cases", s["total"])
    m[1].metric("New", new)
    m[2].metric("Urgent", urgent)
    m[3].metric("Feedback 👍 / 👎", f"{s['feedback_up']} / {s['feedback_down']}")
    m[4].metric("Avg intake", f"{s['avg_intake_seconds']:.1f}s")

    st.subheader("Cases per module")
    if s["per_module"]:
        st.bar_chart(pd.DataFrame({"cases": s["per_module"]}))

    a, b = st.columns(2)
    a.subheader("Per status")
    a.dataframe(pd.DataFrame(sorted(s["per_status"].items()), columns=["status", "cases"]),
                use_container_width=True, hide_index=True)
    b.subheader("Per volunteer")
    b.dataframe(pd.DataFrame([{"volunteer": v["name"], "active load": v["load"],
                               "total cases": s["per_volunteer"].get(v["name"], 0)}
                              for v in db.volunteers()]),
                use_container_width=True, hide_index=True)

    from ui import hooks
    extras = getattr(hooks, "admin_extras", None)
    if callable(extras):
        extras()
