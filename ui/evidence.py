"""Evidence panel: what the filing needs, what the client has uploaded, annexure index."""
from __future__ import annotations

import streamlit as st

from agent import evidence
from db import db
from ui import theme


def _checklist(case: dict, refresh: bool = False) -> list[dict]:
    """One Haiku call per case per session; the tick marks are recomputed every rerun."""
    key = f"evchk{case['id']}"
    if refresh or key not in st.session_state:
        with st.spinner("Haiku is listing the documents this filing needs…"):
            st.session_state[key] = evidence.checklist(case)
    done = evidence._matched_items(case["id"])
    for row in st.session_state[key]:
        row["have"] = evidence._norm(row["item"]) in done
    return st.session_state[key]


def render_evidence(case: dict) -> None:
    """Evidence tab of the case file: checklist, uploads, annexure index."""
    if not case:
        return
    cid = case["id"]

    rows = _checklist(case)
    have = sum(1 for r in rows if r["have"])
    theme.stat_cards([
        {"label": "Documents needed", "value": len(rows)},
        {"label": "Collected", "value": have,
         "delta": "ready to annex" if have else "nothing yet", "tone": "ok" if have else "muted"},
        {"label": "Still missing", "value": len(rows) - have,
         "delta": "ask the client" if have < len(rows) else "complete",
         "tone": "warn" if have < len(rows) else "ok"},
    ])
    st.write("")

    with theme.card("What this filing needs", "दस्तावेज़ सूची - hover an item for why it matters."):
        for i, row in enumerate(rows):
            st.checkbox(row["item"], value=row["have"], disabled=True, key=f"ev{cid}_{i}",
                        help=row["why"])

    with theme.card("Upload annexures", "Photos, PDFs or text. Claude labels and files each one."):
        files = st.file_uploader("Choose files", accept_multiple_files=True, key=f"evup{cid}",
                                 label_visibility="collapsed")
        known = {a["filename"] for a in db.list_annexures(cid)}
        for f in files or []:
            if evidence.safe_name(f.name) in known:
                continue  # already labelled; Streamlit re-delivers the file on every rerun
            with st.spinner(f"Labelling {f.name}…"):
                try:
                    out = evidence.label_upload(cid, f.name, f.getvalue(),
                                                f.type or "application/octet-stream")
                    st.success(f"{out['label']} ({out['kind']})"
                               + (f" → {out['matches_item']}" if out["matches_item"] else ""))
                    _checklist(case)
                except Exception as e:
                    st.error(f"Could not label {f.name}: {e}")

    stored = db.list_annexures(cid)
    if not stored:
        theme.empty_state("📎", "No annexures uploaded yet",
                          "Upload what the client brought; the checklist ticks itself.")
        return

    theme.section("Annexure index", f"{len(stored)} document(s) on file · अनुलग्नक सूची")
    for n, a in enumerate(stored, 1):
        with st.container(border=True):
            st.markdown(f"**A-{n} · {a['label']}**")
            theme.badges(theme.badge(a["kind"], "info"),
                         theme.badge(a["matches_item"], "ok") if a.get("matches_item") else "")
            if a.get("summary"):
                st.caption(a["summary"])

    if st.button("Attach annexure index to draft", key=f"evidx{cid}"):
        if evidence.attach_annexure_index(cid):
            st.success("Annexure index written into the draft.")
            st.rerun()
        else:
            st.info("Draft already carries the current annexure index.")
