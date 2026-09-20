"""Council panel: run the five-agent review on a case with live progress, show the brief."""
import json

import streamlit as st

from agent.orchestra import SPECIALISTS, council_for_case
from ui import theme

LABELS = {"evidence": "🗂️ Evidence officer", "opponent": "⚔️ Devil's advocate",
          "strategy": "🗺️ Filing strategist", "risk": "🚨 Risk & triage",
          "client_letter": "✉️ Client communicator", "synthesis": "⚖️ Senior counsel"}


def _run(case_id: int, force: bool) -> dict:
    with st.status("Council in session - five agents reading the case…", expanded=True) as box:
        slots = {n: box.empty() for n in list(SPECIALISTS) + ["synthesis"]}
        for n, slot in slots.items():
            slot.write(f"⏳ {LABELS[n]}")

        def done(name, ok, ms):
            slots[name].write(f"{'✅' if ok else '❌'} {LABELS[name]} · {ms / 1000:.1f}s")
        out = council_for_case(case_id, force=force, on_agent_done=done)
        box.update(label=f"Council done in {out['ms'] / 1000:.0f}s", state="complete", expanded=False)
    return out


def _title(key: str) -> str:
    return key.replace("_", " ").capitalize()


def _render_value(value, depth: int = 0) -> None:
    """Specialist answers are small JSON trees - show them as headings and bullets."""
    pad = "  " * depth
    if isinstance(value, dict):
        for k, v in value.items():
            if v in (None, "", [], {}):
                continue
            if isinstance(v, (dict, list)):
                st.markdown(f"{pad}**{_title(str(k))}**")
                _render_value(v, depth + 1)
            else:
                st.markdown(f"{pad}- **{_title(str(k))}:** {v}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                _render_value(item, depth + 1)
                st.markdown("")
            else:
                st.markdown(f"{pad}- {item}")
    else:
        st.markdown(f"{pad}{value}")


def _render_agent(name: str, data) -> None:
    if name == "client_letter" and isinstance(data, dict):
        st.markdown("**हिंदी - the letter the client reads**")
        theme.document(data.get("hindi_letter", ""))
        st.markdown("**English**")
        theme.document(data.get("english_letter", ""))
        checklist = data.get("next_visit_checklist") or []
        if checklist:
            theme.section("Bring to the next visit", "अगली मुलाक़ात में लाएँ")
            for item in checklist:
                st.markdown(f"- {item}")
    elif isinstance(data, (dict, list)):
        _render_value(data)
    else:
        st.json(data, expanded=True)      # unexpected shape: fall back to the raw view


def render_council(case: dict, auto: bool = False) -> None:
    """auto=True runs the council immediately if the case has no stored brief."""
    if not case:
        return
    cid = case["id"]
    stored = json.loads(case["council_json"]) if case.get("council_json") else None

    with theme.card("Counsel council",
                    "Five specialist agents plus a senior counsel who reconciles them."):
        c1, c2 = st.columns([1, 3])
        run = c1.button("Run council" if not stored else "Re-run council", key=f"council{cid}",
                        type="primary" if not stored else "secondary",
                        use_container_width=True)
        if stored:
            c2.caption(f"Last run {stored.get('ran_at', '')} · {stored.get('ms', 0) / 1000:.0f}s · "
                       f"{len(stored.get('agents', {}))}/5 agents")
        else:
            c2.caption("About a minute - the five specialists run in parallel.")

    if run or (auto and not stored):
        try:
            stored = _run(cid, force=bool(stored))
        except RuntimeError as e:
            st.error(f"Council failed: {e}")
            return
    if not stored:
        return

    theme.document(stored["brief_md"])
    if stored.get("errors"):
        st.warning("Agents that failed: "
                   + ", ".join(f"{k} ({v[:60]})" for k, v in stored["errors"].items()))

    agents = stored.get("agents", {})
    if not agents:
        return
    tabs = st.tabs([LABELS[n] for n in agents])
    for tab, (name, data) in zip(tabs, agents.items()):
        with tab:
            _render_agent(name, data)
