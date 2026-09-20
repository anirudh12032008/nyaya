import streamlit as st

from agent.pipeline import run_intake

MODULES = ["auto", "consumer", "police", "tenant"]


def _trace_panel(trace, issues=()):
    with st.expander(f"Agent trace ({sum(t['ms'] for t in trace)} ms)", expanded=False):
        st.table([{"step": t["step"], "model": t["model"], "ms": t["ms"],
                   "": "cached" if t["cached"] else ""} for t in trace])
        if any(t["cached"] for t in trace):
            st.caption(":grey[cached — served from cache/, no API call]")
        if issues:  # stage5b: verifier findings
            st.markdown("**Verifier issues**")
            for i in issues:
                st.markdown(f"- `{i.get('type')}` {i.get('detail')} → {i.get('fix')}")


def _analyse(text, override, answer=None):
    try:
        with st.spinner("Claude is reading the intake…"):
            st.session_state.result = run_intake(
                text, module_override=None if override == "auto" else override, answers=answer)
    except RuntimeError as e:  # API down and nothing cached for this input
        st.error(f"Could not reach Claude and nothing is cached for this text. {e}")
        return
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
    with st.expander("🎤 Voice intake (Hindi)"):  # 5D
        from ui.intake_extras import render_mic
        render_mic()

    pdf_file = st.file_uploader("Rent agreement PDF (optional)", type="pdf")  # stage2
    if pdf_file is not None:
        from agent.tenant import extract_pdf_text
        text = (text + "\n\n" + extract_pdf_text(pdf_file.getvalue())).strip()
        st.caption(f"Attached {pdf_file.name} — its text is appended to the statement.")

    detected = (st.session_state.get("result") or {}).get("classification", {}).get("module")
    col1, col2 = st.columns([2, 1])
    override = col1.selectbox("Module", MODULES,
                              index=MODULES.index(detected) if detected in MODULES else 0)
    if col2.button("Analyse", type="primary", use_container_width=True) and text.strip():
        _analyse(text, override)

    r = st.session_state.get("result")
    if not r:
        return

    v = r.get("verification") or {}
    _trace_panel(r["trace"], v.get("first_issues") or v.get("issues") or [])

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

    if d.get("flags"):  # stage2: tenant clause review
        st.markdown("### Clause flags")
        st.table([{"Clause": x.get("clause", ""), "Issue": x.get("issue", ""),
                   "Rule": x.get("rule_id", ""), "Severity": x.get("severity", "")}
                  for x in d["flags"]])

    if v.get("pass") is True:  # stage5b badge
        st.success("✅ Verified by second agent")
    elif v.get("pass") is False:
        n = len(v.get("first_issues") or v.get("issues") or [])
        st.warning(f"⚠️ Verifier flagged {n} issues (redrafted once)" if v.get("redrafted")
                   else f"⚠️ Verifier flagged {n} issues")
        with st.expander("Verifier issues"):
            for i in v.get("issues") or v.get("first_issues") or []:
                st.markdown(f"- `{i.get('type')}` {i.get('detail')} → {i.get('fix')}")
    elif v:
        st.caption(f"verifier skipped: {v.get('skipped', 'no result')}")

    st.markdown("### Draft")
    st.markdown(d["draft_markdown"])

    if d.get("sp_letter_markdown"):  # stage2: station refused -> BNSS 173(4)
        st.markdown("### Letter to the Superintendent of Police — BNSS 173(4)")
        st.markdown(d["sp_letter_markdown"])

    if d.get("what_to_carry"):  # stage2
        st.markdown("### What to carry to the station")
        for s in d["what_to_carry"]:
            st.markdown(f"- {s}")

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

    from ui.intake_extras import render_similar, render_autopilot  # 5G / 5F
    try:
        render_similar(r)
    except Exception as e:  # never let memory lookups break the draft
        st.caption(f"similar cases unavailable: {e}")
    with st.expander("Filing autopilot preview (mock)"):
        render_autopilot(r)
