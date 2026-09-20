"""Ask Nyaya: chat page over the workspace (tools: cases, statutes, forum, council)."""
import html

import streamlit as st

from agent.chat import chat_turn
from db import db
from ui import theme

STARTERS = ["Which cases are closest to their limitation deadline?",
            "Run the council on the most urgent new case and summarise the brief.",
            "Rs 3.2 lakh ka claim hai — kaunsa forum, kitni fee?",
            "What evidence does the newest consumer case still need before filing?"]

# readable answers + a quiet monospace trace line, scoped to this page
_CSS = f"""
<style>
div[data-testid="stChatMessage"] .stMarkdown {{ font-size:.97rem; line-height:1.7; }}
div[data-testid="stChatMessage"] .stMarkdown li {{ margin-bottom:.25rem; }}
.ny-tool {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.76rem;
            color:{theme.MUTED}; background:#F6F4EF; border:1px solid {theme.LINE};
            border-radius:6px; padding:.22rem .5rem; margin-bottom:.45rem;
            display:inline-block; max-width:100%; overflow-wrap:anywhere; }}
</style>
"""


def _tool_line(calls: list[str]) -> str:
    """🔧 tool → tool, as a small monospace chip."""
    return f'<div class="ny-tool">🔧 {html.escape(" → ".join(calls))}</div>'


def _call_label(name, args) -> str:
    return f"{name}({', '.join(f'{k}={v}' for k, v in args.items())})"


def _transcript():
    """Visible turns only: user text and assistant text (tool rounds are collapsed)."""
    for m in st.session_state.chat_history:
        if isinstance(m["content"], str):
            st.chat_message("user").markdown(m["content"])
        elif m["role"] == "assistant":
            text = "".join(b.get("text", "") for b in m["content"] if b.get("type") == "text")
            calls = [b for b in m["content"] if b.get("type") == "tool_use"]
            with st.chat_message("assistant"):
                if calls:
                    st.markdown(_tool_line([_call_label(b["name"], b["input"]) for b in calls]),
                                unsafe_allow_html=True)
                if text:
                    st.markdown(text)


def render():
    st.markdown(_CSS, unsafe_allow_html=True)
    theme.page_header(
        "Ask Nyaya",
        "Ask in plain Hindi, Hinglish or English. Nyaya reads the clinic's own case files, "
        "statute sections, forums and fees before answering — and can run the review council "
        "or change a case's status when you ask.",
        hindi="जो पूछना है, अपनी भाषा में पूछिए।",
        eyebrow="Nyaya · case assistant",
    )
    st.session_state.setdefault("chat_history", [])

    cases = db.list_cases()
    ids = [None] + [c["id"] for c in cases]
    names = {c["id"]: f"#{c['id']} · {c['client_name']} ({c['module']})" for c in cases}

    with theme.card("", "Pick a case to keep the conversation focused on it, or leave it open "
                        "and Nyaya will look across the whole queue."):
        left, right = st.columns([4, 1])
        focus = left.selectbox("Focus case", ids, format_func=lambda i: names.get(i, "— none —"))
        right.write("")
        if right.button("Clear chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    _transcript()
    prompt = st.chat_input("Ask about a case, a deadline, a fee, or say 'run the council on #3'…")
    if not prompt and not st.session_state.chat_history:
        theme.section("Try one of these", "शुरू करने के लिए")
        cols = st.columns(2)
        for i, s in enumerate(STARTERS):
            with cols[i % 2]:
                with st.container(border=True):
                    if st.button(s, key=f"starter{i}", use_container_width=True):
                        prompt = s
    if not prompt:
        return

    st.chat_message("user").markdown(prompt)
    with st.chat_message("assistant"):
        log = st.empty()
        seen = []

        def on_tool(name, args, result):
            seen.append(_call_label(name, args))
            log.markdown(_tool_line(seen), unsafe_allow_html=True)
        try:
            with st.spinner("Nyaya is working…"):
                reply, st.session_state.chat_history = chat_turn(
                    st.session_state.chat_history, prompt, focus_case_id=focus, on_tool=on_tool)
        except Exception as e:
            st.error(f"Chat failed: {e}")
            return
        st.markdown(reply)
