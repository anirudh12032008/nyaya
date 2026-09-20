"""Stage 4: QR/share links, case templates, public guides, feedback -> prompt hints."""
from __future__ import annotations

import difflib
import json
import re

import pandas as pd
import streamlit as st

from agent import guide, learn
from agent.data import load
from db import db
from pdf.qr import base_url, case_url, qr_for_case

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
    lines = [f"[{(case.get('module') or 'other').upper()} MATTER — template from case "
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
    st.subheader("Share & reuse")
    a, b = st.columns(2)

    if a.button("Use as template", key=f"tpl{case_id}",
                help="Open Intake prefilled with this case's shape, facts blanked"):
        st.query_params.clear()
        st.query_params["prefill"] = template_prefill(case)
        st.rerun()

    b.download_button("Download QR", qr_for_case(case_id), key=f"qr{case_id}",
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


def render_readonly(case_id) -> None:
    """?case=<id>&view=readonly — draft + next steps only, nothing editable."""
    try:
        case = db.get_case(int(case_id))
    except (TypeError, ValueError):
        case = None
    if not case:
        st.error(f"Case #{case_id} not found.")
        return

    st.title(f"Case #{case['id']} · {case.get('client_name') or ''}")
    st.caption(f"{case.get('module')} · shared read-only copy")
    if case.get("deadline"):
        days = db.days_to_deadline(case["deadline"])
        st.markdown(f"**Limitation:** {case['deadline']}"
                    + (f" ({days} days left)" if days is not None else ""))

    st.markdown(case.get("draft_md") or "_No draft stored._")

    steps = _next_steps(case.get("module"))
    if steps:
        st.subheader("Next steps")
        for s in steps:
            st.markdown(f"- {s}")

    st.info(f"Draft prepared by Nyaya for a supervising advocate's review. Not legal advice. "
            f"{guide.CTA}.")


# ---------------------------------------------------------------- public guide route

def render_guide(module: str) -> None:
    """?page=guide-<module> — the generated public how-to page."""
    st.title(f"How to file a {module} complaint in Madhya Pradesh")
    text = guide.path(module).read_text(encoding="utf-8") if guide.path(module).exists() else ""
    if not text.strip():
        st.info(f"No guide generated yet for '{module}'. "
                "A clinic admin can create it from the Admin page.")
        return
    # strip the language markers' own title lines? no — they read fine as sections
    st.markdown(re.sub(r"<!--.*?-->\n?", "", text))  # hide language markers
    st.success(guide.CTA)
    st.caption("General procedural information, not legal advice.")


# ---------------------------------------------------------------- admin extras

def _guide_panel() -> None:
    st.subheader("Public guides")
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
    st.subheader("Most corrected sections")
    rows = [{"module": m, "correction": c["note"], "times": c["count"], "👎": c["down"]}
            for m in MODULES for c in learn.corrections(m)[:5]]
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No feedback notes yet — add one from a case's Feedback box.")

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
