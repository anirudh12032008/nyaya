"""Clinic analytics: the head's read on volume, load and outcomes. All counts come from the DB."""
import pandas as pd
import streamlit as st

from db import db
from ui import theme


def _bar(mapping: dict, label: str) -> None:
    if not mapping:
        st.caption("Nothing recorded yet.")
        return
    df = pd.DataFrame(sorted(mapping.items(), key=lambda kv: -kv[1]),
                      columns=[label, "cases"]).set_index(label)
    st.bar_chart(df, color=theme.NAVY, height=260)


def _workload() -> None:
    vols = db.volunteers()
    if not vols:
        st.caption("No volunteers on the roster.")
        return
    totals = db.stats()["per_volunteer"]
    rows = [{"Volunteer": v["name"], "Active load": v.get("load") or 0,
             "Cases ever held": totals.get(v["name"], 0)} for v in vols]
    ceiling = max([r["Active load"] for r in rows] + [1])
    st.dataframe(
        pd.DataFrame(rows), use_container_width=True, hide_index=True,
        column_config={"Active load": st.column_config.ProgressColumn(
            "Active load", help="Open cases held right now", format="%d",
            min_value=0, max_value=ceiling)})


def _outcomes(cases: list[dict]) -> None:
    """Only cases where an outcome was actually recorded (db.set_outcome)."""
    counts = {}
    for c in cases:
        if c.get("outcome"):
            counts[c["outcome"]] = counts.get(c["outcome"], 0) + 1
    if not counts:
        return
    theme.section("Outcomes", f"{sum(counts.values())} of {len(cases)} cases have a recorded outcome.")
    tones = {"won": "ok", "settled": "ok", "lost": "danger", "withdrawn": "muted"}
    theme.stat_cards([{"label": k, "value": v, "tone": tones.get(k, "muted")}
                      for k, v in sorted(counts.items(), key=lambda kv: -kv[1])])


def render():
    s = db.stats()
    cases = db.list_cases()
    theme.page_header(
        "Clinic analytics",
        "Volume, workload and outcomes — counted from the case file, never estimated.",
        hindi="क्लिनिक का लेखा-जोखा",
        eyebrow="Nyaya · clinic head",
    )

    theme.stat_cards([
        {"label": "Total cases", "value": s["total"]},
        {"label": "New", "value": s["per_status"].get("new", 0), "tone": "info"},
        {"label": "Urgent", "value": len(db.list_cases(urgency="high")), "tone": "danger"},
        {"label": "Feedback 👍 / 👎", "value": f"{s['feedback_up']} / {s['feedback_down']}",
         "tone": "ok"},
        {"label": "Avg intake", "value": f"{s['avg_intake_seconds']:.1f}s", "tone": "accent"},
    ])
    st.write("")

    if not s["total"]:
        theme.empty_state("📊", "No cases on file yet",
                          "The first intake will fill this page — volume, status mix and "
                          "volunteer load all come straight from the case records.")
    else:
        left, right = st.columns(2)
        with left:
            with theme.card("Cases per module", "किस तरह के मामले"):
                _bar(s["per_module"], "module")
        with right:
            with theme.card("Cases per status", "कहाँ तक पहुँचे"):
                _bar(s["per_status"], "status")

        theme.section("Volunteer workload", "Active load = open cases held right now.")
        _workload()
        _outcomes(cases)

    st.divider()
    theme.section("Clinic operations", "Overnight triage and the deadline sentinel.")
    from ui import hooks
    extras = getattr(hooks, "admin_extras", None)
    if callable(extras):
        extras()
