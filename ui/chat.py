"""Ask Nyaya: chat page over the workspace (tools: cases, statutes, forum, council)."""
import streamlit as st

from agent.chat import chat_turn
from db import db
from ui.justice import bot_avatar

STARTERS = ["Which cases are closest to their limitation deadline?",
            "Run the council on the most urgent new case and summarise the brief.",
            "Rs 3.2 lakh ka claim hai — kaunsa forum, kitni fee?",
            "What evidence does the newest consumer case still need before filing?"]


def _transcript():
    """Visible turns only: user text and assistant text (tool rounds are collapsed)."""
    for m in st.session_state.chat_history:
        if isinstance(m["content"], str):
            st.chat_message("user").markdown(m["content"])
        elif m["role"] == "assistant":
            text = "".join(b.get("text", "") for b in m["content"] if b.get("type") == "text")
            calls = [b for b in m["content"] if b.get("type") == "tool_use"]
            with st.chat_message("assistant", avatar=bot_avatar()):
                if calls:
                    st.caption("🔧 " + ", ".join(f"{b['name']}({', '.join(f'{k}={v}' for k, v in b['input'].items())})"
                                                 for b in calls))
                if text:
                    st.markdown(text)


def render():
    st.title("Ask Nyaya")
    st.caption("An agent over the whole workspace: it reads cases, statutes, fees, runs the council, "
               "and updates status when you ask.")
    st.session_state.setdefault("chat_history", [])

    cases = db.list_cases()
    ids = [None] + [c["id"] for c in cases]
    names = {c["id"]: f"#{c['id']} · {c['client_name']} ({c['module']})" for c in cases}
    focus = st.sidebar.selectbox("Focus case", ids, format_func=lambda i: names.get(i, "— none —"))
    if st.sidebar.button("Clear chat"):
        st.session_state.chat_history = []
        st.rerun()

    _transcript()
    prompt = st.chat_input("Ask about a case, a deadline, a fee, or say 'run the council on #3'…")
    if not prompt and not st.session_state.chat_history:
        cols = st.columns(2)
        for i, s in enumerate(STARTERS):
            if cols[i % 2].button(s, key=f"starter{i}", use_container_width=True):
                prompt = s
    if not prompt:
        return

    st.chat_message("user").markdown(prompt)
    with st.chat_message("assistant", avatar=bot_avatar()):
        log = st.empty()
        seen = []

        def on_tool(name, args, result):
            seen.append(f"{name}({', '.join(f'{k}={v}' for k, v in args.items())})")
            log.caption("🔧 " + " → ".join(seen))
        try:
            with st.spinner("Nyaya is working…"):
                reply, st.session_state.chat_history = chat_turn(
                    st.session_state.chat_history, prompt, focus_case_id=focus, on_tool=on_tool)
        except Exception as e:
            st.error(f"Chat failed: {e}")
            return
        st.markdown(reply)
