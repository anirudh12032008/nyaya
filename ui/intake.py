import streamlit as st

from agent.pipeline import run_intake
from ui import theme

MODULES = ["auto", "consumer", "police", "tenant", "labour"]

# Six visible stages of the pipeline. `done` is derived from what actually ran.
STEPS = [
    {"key": "intake", "title": "Understand", "desc": "read the statement"},
    {"key": "triage", "title": "Classify", "desc": "module + urgency"},
    {"key": "evidence", "title": "Extract", "desc": "facts, parties, dates"},
    {"key": "eligibility", "title": "Check", "desc": "forum, fee, free aid"},
    {"key": "draft", "title": "Prepare", "desc": "complaint / notice"},
    {"key": "verify", "title": "Review", "desc": "second agent"},
]

EXAMPLES = {
    "Consumer": "I bought a washing machine for Rs. 28,000 from a showroom in Bhopal on "
                "12 March. It stopped working in a week. The shop refuses to repair or refund.",
    "Police": "Main apne bete ki gumshudgi ki report likhwane thane gaya tha, "
              "lekin police ne FIR darj karne se mana kar diya.",
    "Tenant": "My landlord in Indore is keeping my Rs. 40,000 security deposit and has "
              "cut the water supply to force me to leave before the agreement ends.",
    "Labour": "I worked as a helper at a factory in Jabalpur for 14 months. "
              "Wages for the last three months, about Rs. 33,000, were never paid.",
}


def _done_steps(r):
    """Which of STEPS actually completed, read off the result - never guessed."""
    if not r:
        return set()
    steps = {t["step"] for t in r.get("trace") or []}
    done = {"intake"}
    if "classify" in steps:
        done.add("triage")
    if (r.get("classification") or {}).get("facts"):
        done.add("evidence")
    # eligibility runs in the post-draft hook (case_service), so a saved case is the proof
    if r.get("forum") or st.session_state.get("last_case_id"):
        done.add("eligibility")
    if any(s.startswith("draft") for s in steps):
        done.add("draft")
    if any(s.startswith("verify") for s in steps):
        done.add("verify")
    return done


def _trace_panel(trace, issues=()):
    with st.expander(f"Agent trace ({sum(t['ms'] for t in trace)} ms)", expanded=False):
        st.dataframe(
            [{"step": t["step"], "model": t["model"], "ms": t["ms"],
              "cached": bool(t["cached"])} for t in trace],
            use_container_width=True, hide_index=True)
        if any(t["cached"] for t in trace):
            st.caption("cached - served from cache/, no API call")
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
        st.error("Could not reach Claude, and this statement is not in the local cache. "
                 f"Try again when the connection is back. ({e})")
        return
    r = st.session_state.result
    if r.get("draft"):
        try:
            from ui.hooks import on_draft_complete  # Stage 3 persists the case here
            on_draft_complete(r)
        except Exception as e:  # a broken hook must never kill the draft
            st.warning(f"post-draft hook failed: {e}")


def _seed_box():
    """Prefill the box once: Home hands off via intake_text_seed, links via ?prefill=."""
    seed = st.session_state.pop("intake_text_seed", "")
    if not seed and "intake_text" not in st.session_state:
        seed = st.query_params.get("prefill", "")
    if seed:
        st.session_state["intake_text"] = seed


def _fill_example(name):
    st.session_state["intake_text"] = EXAMPLES[name]


def _input_card():
    """Returns (text, override, clicked)."""
    text = ""
    with theme.card(theme.t("Client's statement"),
                    "Hindi, Hinglish or English - write it the way the client said it."):
        tab_type, tab_speak, tab_upload = st.tabs(["Type", "Speak", "Upload"])

        with tab_type:
            text = st.text_area("Statement", height=210, key="intake_text",
                                label_visibility="collapsed",
                                placeholder="जो हुआ वह यहाँ लिखें / Write what happened…")
            st.caption(f"{len(text)} characters")
            st.markdown(f'<div class="ny-kv">{theme.t("Start from an example")}</div>', unsafe_allow_html=True)
            for col, name in zip(st.columns(len(EXAMPLES)), EXAMPLES):
                col.button(name, key=f"eg_{name}", use_container_width=True,
                           on_click=_fill_example, args=(name,))

        with tab_speak:
            from ui.intake_extras import render_mic  # 5D
            render_mic()

        with tab_upload:
            pdf_file = st.file_uploader(theme.t("Rent agreement PDF (optional)"), type="pdf")  # stage2
            if pdf_file is not None:
                from agent.tenant import extract_pdf_text
                text = (text + "\n\n" + extract_pdf_text(pdf_file.getvalue())).strip()
                st.caption(f"Attached {pdf_file.name} - its text is appended to the statement.")
            else:
                st.caption(theme.t("A rent agreement helps the tenant module flag unfair clauses."))

        detected = (st.session_state.get("result") or {}).get("classification", {}).get("module")
        col1, col2 = st.columns([2, 1])
        override = col1.selectbox("Module", MODULES,
                                  index=MODULES.index(detected) if detected in MODULES else 0,
                                  help="'auto' lets the classifier decide.")
        col2.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
        clicked = col2.button("Analyse", type="primary", use_container_width=True)
    return text, override, clicked


def _summary_card(r, cls, d, f, v):
    """Right-hand rail: what this case is, and what to do about it."""
    with theme.card("Case summary", "क्लाइंट को क्या बताना है"):
        theme.badges((cls.get("module", "?"), "info"),
                     (f"urgency: {cls.get('urgency', '?')}",
                      "danger" if str(cls.get("urgency")).lower() in ("high", "urgent") else "warn"),
                     (cls.get("language", "?"), "muted"),
                     (cls.get("jurisdiction", "?"), "muted"))

        if f:
            theme.stat_cards([{"label": "Forum", "value": f.get("forum", " - ")},
                              {"label": "Fee", "value": f"Rs.{f.get('fee_inr', ' - ')}"},
                              {"label": "Limitation", "value": f"{f.get('limitation_years', ' - ')} yrs"}])
            if f.get("amount_unknown"):
                st.warning("Claim amount unknown - forum shown is provisional "
                           "(District Commission).")

        if d.get("deadline_iso"):
            st.markdown(theme.deadline_badge(_days_left(d["deadline_iso"])) +
                        " " + theme.kv("expires", d["deadline_iso"]),
                        unsafe_allow_html=True)

        # verification
        if v.get("pass") is True:  # stage5b badge
            st.markdown(theme.badge("verified by second agent", "ok", solid=True),
                        unsafe_allow_html=True)
        elif v.get("pass") is False:
            n = len(v.get("first_issues") or v.get("issues") or [])
            label = f"{n} issues flagged - redrafted once" if v.get("redrafted") \
                else f"{n} issues flagged"
            st.markdown(theme.badge(label, "warn", solid=True), unsafe_allow_html=True)

        if d.get("next_steps"):
            st.markdown(f"**{theme.t('Next steps')}**")
            for s_ in d["next_steps"][:3]:
                st.markdown(f"- {s_}")

        with st.expander("More detail: sections, what to carry, Hindi summary"):
            if d.get("sections"):
                st.markdown("**Sections relied on**")
                for s_ in d["sections"]:
                    st.markdown(f"- **{s_.get('id')}** - {s_.get('why', '')}")
            if r.get("sections_dropped"):
                st.warning("Dropped (not in our statute data): " + ", ".join(
                    str(x) for x in r["sections_dropped"]))
            if len(d.get("next_steps") or []) > 3:
                st.markdown("**All next steps**")
                for s_ in d["next_steps"]:
                    st.markdown(f"- {s_}")
            if d.get("what_to_carry"):  # stage2
                st.markdown("**What to carry**")
                for s_ in d["what_to_carry"]:
                    st.markdown(f"- {s_}")
            if d.get("hindi_summary"):
                st.markdown("**क्लाइंट के लिए सारांश**")
                theme.quote(d["hindi_summary"])
            if v.get("pass") is False:
                st.markdown("**Verifier issues**")
                for i in v.get("issues") or v.get("first_issues") or []:
                    st.markdown(f"- `{i.get('type')}` {i.get('detail')} → {i.get('fix')}")
            elif v and v.get("pass") is None:
                st.caption(f"verifier skipped: {v.get('skipped', 'no result')}")

        from pdf.render import draft_to_pdf
        st.download_button("Download PDF",
                           draft_to_pdf(d["draft_markdown"],
                                        {**(f or {}), "deadline_iso": d.get("deadline_iso")}),
                           file_name="nyaya-draft.pdf", mime="application/pdf",
                           type="primary", use_container_width=True)


def _days_left(deadline_iso):
    from datetime import date
    try:
        y, m, dd = (int(x) for x in str(deadline_iso)[:10].split("-"))
        return (date(y, m, dd) - date.today()).days
    except Exception:
        return None


def render():
    theme.page_header("New intake",
                      "Paste or speak what the client said. Claude classifies it, checks the "
                      "forum and limitation, and prepares a draft you review.",
                      hindi="क्लाइंट की बात यहाँ लिखें", eyebrow="Legal aid clinic")

    _seed_box()
    text, override, clicked = _input_card()
    if clicked and text.strip():
        _analyse(text, override)
    elif clicked:
        st.error(theme.t("Write or paste the client's statement first."))

    r = st.session_state.get("result")
    st.write("")
    theme.agent_strip(STEPS, done=_done_steps(r))

    if not r:
        theme.empty_state("📄", "No intake analysed yet",
                          "The draft, forum and deadline appear here once you press Analyse.")
        return

    v = r.get("verification") or {}

    if r.get("missing_fact") and not r.get("draft"):
        with theme.card("One question before drafting", "एक सवाल"):
            st.info(r["missing_fact"])
            ans = st.text_input("Answer", key="followup")
            if st.button(theme.t("Continue"), type="primary") and ans.strip():
                _analyse(text, override, answer=ans)
                st.rerun()
        return

    cls = r["classification"]
    d = r.get("draft")
    if not d:
        theme.empty_state("🛠", f"No drafting for '{cls['module']}' yet",
                          "Classification is done; this module's drafting arrives in Stage 2.")
        return

    f = r.get("forum")
    _summary_card(r, cls, d, f, v)

    with st.expander("Read the draft", expanded=False):
        theme.document(d["draft_markdown"])
    if d.get("sp_letter_markdown"):  # stage2: station refused -> BNSS 173(4)
        with st.expander("Letter to the Superintendent of Police - BNSS 173(4)"):
            theme.document(d["sp_letter_markdown"])
    if d.get("demand_letter_markdown"):  # labour: pre-litigation notice to the employer
        with st.expander("Demand letter to the employer"):
            theme.document(d["demand_letter_markdown"])
    if d.get("flags"):  # stage2: tenant clause review
        with st.expander("Clause flags in the agreement"):
            st.dataframe([{"Clause": x.get("clause", ""), "Issue": x.get("issue", ""),
                           "Rule": x.get("rule_id", ""), "Severity": x.get("severity", "")}
                          for x in d["flags"]],
                         use_container_width=True, hide_index=True)

    from ui.intake_extras import render_similar, render_autopilot  # 5G / 5F
    with st.expander("Similar past cases"):
        try:
            render_similar(r)
        except Exception as e:  # never let memory lookups break the draft
            st.caption(f"similar cases unavailable: {e}")
    with st.expander("Filing autopilot preview (mock)"):
        render_autopilot(r)

    if st.session_state.get("last_case_id"):  # orchestra: council runs itself right after the draft
        from db import db
        from ui.orchestra import render_council
        with st.expander("AI council review"):
            render_council(db.get_case(st.session_state["last_case_id"]), auto=True)

    _trace_panel(r["trace"], v.get("first_issues") or v.get("issues") or [])
