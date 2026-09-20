"""Evidence panel: what the filing needs, what the client has uploaded, annexure index."""
from __future__ import annotations

import streamlit as st

from agent import evidence
from db import db


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
    """Wire into ui.hooks.extra_case_actions."""
    if not case:
        return
    cid = case["id"]
    st.subheader("Evidence & annexures")

    rows = _checklist(case)
    have = sum(1 for r in rows if r["have"])
    st.caption(f"{have}/{len(rows)} collected")
    for i, row in enumerate(rows):
        st.checkbox(row["item"], value=row["have"], disabled=True, key=f"ev{cid}_{i}",
                    help=row["why"])

    files = st.file_uploader("Upload annexures", accept_multiple_files=True,
                             key=f"evup{cid}", help="Photos, PDFs or text. Claude labels each one.")
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
    if stored:
        st.markdown("**Uploaded**")
        for n, a in enumerate(stored, 1):
            st.markdown(f"- **A-{n}** {a['label']} · `{a['kind']}` · {a.get('summary') or ''}"
                        + (f"  \n  ↳ {a['matches_item']}" if a.get("matches_item") else ""))
        if st.button("Attach annexure index to draft", key=f"evidx{cid}"):
            if evidence.attach_annexure_index(cid):
                st.success("Annexure index written into the draft.")
                st.rerun()
            else:
                st.info("Draft already carries the current annexure index.")
    else:
        st.caption("No annexures uploaded yet.")
