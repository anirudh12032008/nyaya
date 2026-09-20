"""Council panel: run the five-agent review on a case with live progress, show the brief."""
import json

import streamlit as st

from agent.orchestra import SPECIALISTS, council_for_case

LABELS = {"evidence": "🗂️ Evidence officer", "opponent": "⚔️ Devil's advocate",
          "strategy": "🗺️ Filing strategist", "risk": "🚨 Risk & triage",
          "client_letter": "✉️ Client communicator", "synthesis": "⚖️ Senior counsel"}


def _run(case_id: int, force: bool) -> dict:
    with st.status("Council in session — five agents reading the case…", expanded=True) as box:
        slots = {n: box.empty() for n in list(SPECIALISTS) + ["synthesis"]}
        for n, slot in slots.items():
            slot.write(f"⏳ {LABELS[n]}")

        def done(name, ok, ms):
            slots[name].write(f"{'✅' if ok else '❌'} {LABELS[name]} · {ms / 1000:.1f}s")
        out = council_for_case(case_id, force=force, on_agent_done=done)
        box.update(label=f"Council done in {out['ms'] / 1000:.0f}s", state="complete", expanded=False)
    return out


def render_council(case: dict, auto: bool = False) -> None:
    """auto=True runs the council immediately if the case has no stored brief."""
    if not case:
        return
    cid = case["id"]
    st.subheader("Counsel council")
    stored = json.loads(case["council_json"]) if case.get("council_json") else None
    c1, c2 = st.columns([1, 3])
    run = c1.button("Run council" if not stored else "Re-run council", key=f"council{cid}",
                    type="primary" if not stored else "secondary")
    if stored:
        c2.caption(f"Last run {stored.get('ran_at', '')} · {stored.get('ms', 0) / 1000:.0f}s · "
                   f"{len(stored.get('agents', {}))}/5 agents")
    if run or (auto and not stored):
        try:
            stored = _run(cid, force=bool(stored))
        except RuntimeError as e:
            st.error(f"Council failed: {e}")
            return
    if not stored:
        c2.caption("Five specialist agents + a synthesiser, ~1 minute, all in parallel.")
        return

    st.markdown(stored["brief_md"])
    if stored.get("errors"):
        st.warning("Agents that failed: " + ", ".join(f"{k} ({v[:60]})" for k, v in stored["errors"].items()))

    agents = stored.get("agents", {})
    tabs = st.tabs([LABELS[n] for n in agents])
    for tab, (name, data) in zip(tabs, agents.items()):
        with tab:
            if name == "client_letter":
                st.markdown("**हिंदी**"); st.info(data.get("hindi_letter", ""))
                st.markdown("**English**"); st.info(data.get("english_letter", ""))
                for item in data.get("next_visit_checklist", []):
                    st.markdown(f"- {item}")
            else:
                st.json(data, expanded=True)
