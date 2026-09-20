"""Stage 4: QR/share links, case templates, public guides, feedback -> prompt hints."""
from __future__ import annotations

import difflib
import html
import json
import re

import pandas as pd
import streamlit as st

from agent import guide, learn
from agent.data import load
from db import db
from pdf.qr import base_url, case_url, qr_for_case
from ui import theme

MODULES = ["consumer", "police", "tenant", "labour"]

_MONEY = re.compile(r"(?:rs\.?|₹|inr)\s*[\d,]+(?:\.\d+)?(?:\s*(?:lakh|crore|thousand))?", re.I)
_DATE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
                   r"|\d{1,2}\s+[A-Z][a-z]+\s+\d{4}|[A-Z][a-z]+\s+\d{4})\b")


# ---------------------------------------------------------------- templates

def _facts(case: dict) -> dict:
    try:
        f = json.loads(case.get("facts_json") or "{}")
        return f if isinstance(f, dict) else {}
    except ValueError:
        return {}


def _party_names(facts: dict) -> list[str]:
    out = []
    for p in facts.get("parties") or []:
        name = (p.get("name") if isinstance(p, dict) else str(p) if p else "") or ""
        if name.strip():
            out.append(name.strip())
    return out


def blank_facts(text: str, facts: dict) -> str:
    """Blank the case-specific bits so the text can be reused as a template."""
    text = text or ""
    for name in sorted(_party_names(facts) + [facts.get("client_name") or ""], key=len, reverse=True):
        if len(name) > 2:
            text = re.sub(re.escape(name), "[NAME]", text, flags=re.I)
    text = _MONEY.sub("[AMOUNT]", text)
    text = _DATE.sub("[DATE]", text)
    return text


def template_prefill(case: dict) -> str:
    """Intake text built from this case's module + facts, with the specifics blanked."""
    facts = _facts(case)
    facts.setdefault("client_name", case.get("client_name"))
    lines = [f"[{(case.get('module') or 'other').upper()} MATTER - template from case "
             f"#{case.get('id')}; replace every bracket]",
             blank_facts(facts.get("what_happened") or case.get("summary") or "", facts)]
    if _party_names(facts):
        lines.append("Parties: [NAME] against [NAME].")
    if facts.get("amount_inr") is not None:
        lines.append("Amount involved: Rs [AMOUNT].")
    if facts.get("date_of_cause"):
        lines.append("Date of cause of action: [DATE].")
    return "\n".join(x for x in lines if x.strip())


# ---------------------------------------------------------------- case detail extras

def extra_case_actions(case: dict) -> None:
    """Wired into the Cases detail view via ui.hooks.extra_case_actions."""
    case_id = case["id"]
    with theme.card("Share & reuse", "Give the client a link or a QR; reuse the shape of this file."):
        a, b = st.columns(2)
        if a.button("Use as template", key=f"tpl{case_id}", use_container_width=True,
                    help="Open Intake prefilled with this case's shape, facts blanked"):
            st.query_params.clear()
            st.query_params["prefill"] = template_prefill(case)
            st.rerun()

        b.download_button("Download QR", qr_for_case(case_id), key=f"qr{case_id}",
                          use_container_width=True,
                          file_name=f"nyaya-case-{case_id}.png", mime="image/png")

        st.caption("Read-only share link (draft + next steps, no controls):")
        st.code(f"{base_url()}/?case={case_id}&view=readonly", language=None)
        st.caption("QR on the PDF opens:")
        st.code(case_url(case_id), language=None)


# ---------------------------------------------------------------- read-only share view

def _next_steps(module: str) -> list[str]:
    p = load("portals").get(module or "", {})
    steps = []
    if p.get("documents"):
        steps.append("Collect: " + "; ".join(p["documents"]))
    if p.get("portal_url"):
        steps.append(f"File online at {p['portal_url']}")
    if p.get("portal_note"):
        steps.append(p["portal_note"])
    if p.get("fee_rule"):
        steps.append(f"Fee: {p['fee_rule']}")
    if p.get("deadline_rule"):
        steps.append(f"Deadline: {p['deadline_rule']}")
    return steps


def _masthead(hindi: str = "") -> None:
    """Public pages have no sidebar, so they carry the clinic's name themselves."""
    hi = (f'<div style="font-family:\'Source Serif 4\',Georgia,serif;color:{theme.MUTED};'
          f'font-size:1rem;margin-top:.15rem">{hindi}</div>') if hindi else ""
    st.markdown(
        '<div style="display:flex;align-items:center;gap:.7rem;padding-bottom:.8rem;'
        f'border-bottom:1px solid {theme.LINE};margin-bottom:1.2rem">'
        '<div style="font-size:2rem">⚖️</div><div>'
        f'<div style="font-family:\'Source Serif 4\',Georgia,serif;font-size:1.5rem;'
        f'font-weight:700;line-height:1;color:{theme.NAVY}">NYAYA '
        f'<span style="font-size:1.1rem;color:{theme.BRASS}">न्याय</span></div>'
        f'<div style="font-size:.74rem;letter-spacing:.09em;text-transform:uppercase;'
        f'color:{theme.MUTED};font-weight:600">Legal aid clinic · Madhya Pradesh</div>'
        f'</div></div>{hi}', unsafe_allow_html=True)


def _public_footer() -> None:
    st.write("")
    theme.badges((guide.CTA, "ok"), ("अपने नज़दीकी विधिक सहायता क्लिनिक से मदद लें", "ok"))
    st.caption("General procedural information prepared for a supervising advocate's review. "
               "This is not legal advice. · यह कानूनी सलाह नहीं है।")


def render_readonly(case_id) -> None:
    """?case=<id>&view=readonly - draft + next steps only, nothing editable."""
    try:
        case = db.get_case(int(case_id))
    except (TypeError, ValueError):
        case = None
    if not case:
        _masthead()
        st.error(f"Case #{case_id} not found.")
        return

    _masthead()
    theme.page_header(
        f"Your case file · {case.get('client_name') or ''}".strip(" ·"),
        "A read-only copy of what the clinic has prepared for you.",
        hindi="आपकी फाइल की नकल - इसे बदला नहीं जा सकता।",
        eyebrow=f"Case #{case['id']}",
    )

    days = db.days_to_deadline(case.get("deadline")) if case.get("deadline") else None
    theme.badges(
        theme.badge(case.get("module") or "matter", "info"),
        theme.badge(f"last date to file: {case['deadline']}", "warn") if case.get("deadline") else "",
        theme.deadline_badge(days) if case.get("deadline") else "",
    )
    st.write("")

    theme.section("The letter prepared for you", "आपके लिए तैयार किया गया मसौदा")
    if (case.get("draft_md") or "").strip():
        theme.document(case["draft_md"])
    else:
        theme.empty_state("📄", "No draft yet",
                          "The clinic has not finished writing this one. Please check back, "
                          "or ask the volunteer who took your details.")

    steps = _next_steps(case.get("module"))
    if steps:
        theme.section("What to do next", "आगे क्या करना है")
        for i, s in enumerate(steps, 1):
            st.markdown(
                f'<div style="display:flex;gap:.8rem;align-items:flex-start;'
                f'background:{theme.SURFACE};border:1px solid {theme.LINE};border-radius:10px;'
                f'padding:.8rem 1rem;margin-bottom:.5rem">'
                f'<div style="font-family:\'Source Serif 4\',Georgia,serif;font-size:1.3rem;'
                f'font-weight:700;color:{theme.BRASS};line-height:1.2">{i}</div>'
                f'<div style="font-size:1rem;line-height:1.6">{html.escape(s)}</div></div>',
                unsafe_allow_html=True)

    _public_footer()


# ---------------------------------------------------------------- public guide route

def render_guide(module: str) -> None:
    """?page=guide-<module> - the generated public how-to page."""
    _masthead()
    hi_module = guide.HI_MODULE.get(module, module)
    theme.page_header(
        f"How to file a {module} complaint in Madhya Pradesh",
        "Step by step, in plain language. Free to read, free to share.",
        hindi=f"मध्य प्रदेश में {hi_module} शिकायत कैसे दर्ज करें",
        eyebrow="Public guide · जन मार्गदर्शिका",
    )

    text = guide.path(module).read_text(encoding="utf-8") if guide.path(module).exists() else ""
    if not text.strip():
        theme.empty_state("📘", "This guide is not ready yet",
                          f"No '{module}' guide has been written. A clinic admin can generate it.")
        return

    langs = guide.read(module) or {}
    if langs.get("hi") and langs.get("en"):
        hi, en = st.tabs(["हिंदी", "English"])          # Hindi first: most readers here read Hindi
        with hi:
            theme.document(langs["hi"])
        with en:
            theme.document(langs["en"])
    else:
        # single-language or unmarked file: fall back to the whole text, markers hidden
        theme.document(re.sub(r"<!--.*?-->\n?", "", text))

    _public_footer()


# ---------------------------------------------------------------- admin extras

def _guide_panel() -> None:
    with theme.card("Public guides", "Citizen-facing how-to pages, one per module (EN + HI)."):
        for module in MODULES:
            c1, c2, c3 = st.columns([1, 1, 2])
            c1.write(module)
            if c2.button("Generate guide", key=f"gen{module}"):
                with st.spinner(f"Sonnet is writing the {module} guide (EN + HI)…"):
                    try:
                        guide.generate(module, refresh=True)
                        st.success(f"Wrote {guide.path(module).relative_to(guide.ROOT)}")
                    except Exception as e:
                        st.error(f"Guide generation failed: {e}")
            if guide.path(module).exists():
                c3.markdown(f"[Open guide]({base_url()}/?page=guide-{module})")
            else:
                c3.caption("not generated yet")


def _learning_panel() -> None:
    with theme.card("Most corrected sections",
                    "What volunteers keep fixing - fed back into the drafting prompts."):
        rows = [{"module": m, "correction": c["note"], "times": c["count"], "👎": c["down"]}
                for m in MODULES for c in learn.corrections(m)[:5]]
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No feedback notes yet - add one from a case's Feedback box.")

        module = st.selectbox("Module prompt to update", MODULES, key="hintmodule")
        if st.button("Regenerate prompt hints"):
            try:
                old, new = learn.apply_hints(module)
            except FileNotFoundError:
                st.error(f"No prompt file at agent/prompts/draft_{module}.md")
                return
            if old == new:
                st.info("Prompt already up to date with the current feedback.")
                return
            diff = difflib.unified_diff(old.splitlines(), new.splitlines(),
                                        fromfile=f"draft_{module}.md (before)",
                                        tofile=f"draft_{module}.md (after)", lineterm="")
            st.code("\n".join(diff), language="diff")


def admin_extras() -> None:
    """Wired into the Admin page via ui.hooks.admin_extras."""
    st.divider()
    _guide_panel()
    st.divider()
    _learning_panel()
