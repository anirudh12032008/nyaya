import streamlit as st

from agent.pipeline import run_intake

MODULES = ["auto", "consumer", "police", "tenant"]


def _trace_panel(trace):
    with st.expander(f"Agent trace ({sum(t['ms'] for t in trace)} ms)", expanded=False):
        st.table([{"step": t["step"], "model": t["model"], "ms": t["ms"],
                   "": "cached" if t["cached"] else ""} for t in trace])
        if any(t["cached"] for t in trace):
            st.caption(":grey[cached — served from cache/, no API call]")


def _analyse(text, override, answer=None):
    with st.spinner("Claude is reading the intake…"):
        st.session_state.result = run_intake(
            text, module_override=None if override == "auto" else override, answers=answer)
    r = st.session_state.result
    if r.get("draft"):
        try:
            from ui.hooks import on_draft_complete  # Stage 3 persists the case here
            on_draft_complete(r)
        except Exception as e:  # a broken hook must never kill the draft
            st.warning(f"post-draft hook failed: {e}")


def render():
    st.title("Intake")
    st.caption("Paste what the client said — Hindi, Hinglish or English.")

    prefill = st.query_params.get("prefill", "")
    text = st.text_area("Client's statement", value=prefill, height=160, key="intake_text")

    detected = (st.session_state.get("result") or {}).get("classification", {}).get("module")
    col1, col2 = st.columns([2, 1])
    override = col1.selectbox("Module", MODULES,
                              index=MODULES.index(detected) if detected in MODULES else 0)
    if col2.button("Analyse", type="primary", use_container_width=True) and text.strip():
        _analyse(text, override)

    r = st.session_state.get("result")
    if not r:
        return

    _trace_panel(r["trace"])

    if r.get("missing_fact") and not r.get("draft"):
        st.info(f"**One question:** {r['missing_fact']}")
        ans = st.text_input("Answer", key="followup")
        if st.button("Continue") and ans.strip():
            _analyse(text, override, answer=ans)
            st.rerun()
        return

    cls = r["classification"]
    st.write(f"**Module:** {cls['module']} · **Urgency:** {cls['urgency']} · "
             f"**Language:** {cls['language']} · **Jurisdiction:** {cls['jurisdiction']}")

    f = r.get("forum")
    if f:
        c = st.columns(3)
        c[0].metric("Forum", f["forum"])
        c[1].metric("Fee", f"Rs.{f['fee_inr']}")
        c[2].metric("Limitation", f"{f['limitation_years']} years")
        if f.get("amount_unknown"):
            st.warning("Claim amount unknown — forum shown is provisional (District Commission).")

    d = r.get("draft")
    if not d:
        st.info(f"Module '{cls['module']}' drafting arrives in Stage 2.")
        return

    st.markdown("### Draft")
    st.markdown(d["draft_markdown"])

    st.markdown("### Sections relied on")
    for s in d["sections"]:
        st.markdown(f"- **{s.get('id')}** — {s.get('why', '')}")
    if r.get("sections_dropped"):
        st.warning("Dropped (not in our statute data): " + ", ".join(
            str(x) for x in r["sections_dropped"]))

    if d.get("next_steps"):
        st.markdown("### Next steps")
        for s in d["next_steps"]:
            st.markdown(f"- {s}")

    if d.get("hindi_summary"):
        st.markdown("### Client summary (Hindi)")
        st.info(d["hindi_summary"])

    if d.get("deadline_iso"):
        st.markdown(f"**Limitation expires:** {d['deadline_iso']}")

    from pdf.render import draft_to_pdf
    st.download_button("Download PDF",
                       draft_to_pdf(d["draft_markdown"],
                                    {**(f or {}), "deadline_iso": d.get("deadline_iso")}),
                       file_name="nyaya-draft.pdf", mime="application/pdf")
