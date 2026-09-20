"""Ask Nyaya: a floating chat bubble (bottom-right) over the workspace.

Mounted once by app.py on every internal page. The FAB toggles a fixed panel;
state lives in session_state so it survives the reruns Streamlit does on every
button press.
"""
import html

import streamlit as st

from agent.chat import chat_turn
from ui import theme

STARTERS = ["Cases closest to their limitation deadline?",
            "Rs 3.2 lakh ka claim - kaunsa forum, kitni fee?"]

_CSS = f"""
<style>
/* the bubble */
.st-key-ny_fab {{ position:fixed; right:24px; bottom:24px; width:58px; z-index:1002; }}
.st-key-ny_fab button {{
  width:58px; height:58px; min-height:58px; border-radius:50%; padding:0;
  background:{theme.NAVY} !important; border:1px solid {theme.NAVY} !important;
  color:#fff !important; font-size:1.35rem; line-height:1;
  box-shadow:0 8px 22px rgba(31,58,95,.32);
}}
.st-key-ny_fab button:hover {{ background:#16293F !important; }}

/* the panel */
.st-key-ny_panel {{
  position:fixed; right:24px; bottom:94px; width:392px; z-index:1001;
  background:{theme.SURFACE}; border:1px solid {theme.LINE}; border-radius:14px;
  box-shadow:0 18px 46px rgba(26,29,33,.18); padding:.85rem 1rem 1rem;
}}
.st-key-ny_panel .stChatMessage {{ padding:.25rem 0; }}
.st-key-ny_panel .stMarkdown {{ font-size:.92rem; line-height:1.62; }}
.st-key-ny_panel .stMarkdown li {{ margin-bottom:.2rem; }}
.st-key-ny_panel div[data-testid="stVerticalBlockBorderWrapper"] {{ border:0; }}
@media (max-width:700px) {{
  .st-key-ny_panel {{ left:12px; right:12px; width:auto; bottom:90px; }}
}}
.ny-tool {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.72rem;
            color:{theme.MUTED}; background:#F6F4EF; border:1px solid {theme.LINE};
            border-radius:6px; padding:.2rem .45rem; margin-bottom:.4rem;
            display:inline-block; max-width:100%; overflow-wrap:anywhere; }}
.ny-chat-head {{ font-family:'Source Serif 4',Georgia,serif; font-size:1.05rem;
                 font-weight:700; color:{theme.INK}; line-height:1.2; }}
.ny-chat-sub {{ font-size:.74rem; color:{theme.MUTED}; }}
</style>
"""


def _call_label(name, args) -> str:
    return f"{name}({', '.join(f'{k}={v}' for k, v in args.items())})"


def _tool_line(calls: list[str]) -> str:
    return f'<div class="ny-tool">🔧 {html.escape(" → ".join(calls))}</div>'


def _transcript():
    """Visible turns only: user text and assistant text (tool rounds collapsed)."""
    for m in st.session_state.chat_history:
        if isinstance(m["content"], str):
            st.chat_message("user", avatar=theme.AVATARS["user"]).markdown(m["content"])
        elif m["role"] == "assistant":
            text = "".join(b.get("text", "") for b in m["content"] if b.get("type") == "text")
            calls = [b for b in m["content"] if b.get("type") == "tool_use"]
            with st.chat_message("assistant", avatar=theme.AVATARS["assistant"]):
                if calls:
                    st.markdown(_tool_line([_call_label(b["name"], b["input"]) for b in calls]),
                                unsafe_allow_html=True)
                if text:
                    st.markdown(text)


def _focus_case_id():
    """Keep the conversation on the case the user is looking at, if any."""
    raw = st.query_params.get("case")
    return int(raw) if raw and str(raw).isdigit() else None


def _answer(prompt: str, focus):
    st.chat_message("user", avatar=theme.AVATARS["user"]).markdown(prompt)
    with st.chat_message("assistant", avatar=theme.AVATARS["assistant"]):
        log, seen = st.empty(), []

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


def render_dock():
    """Floating Ask-Nyaya bubble + panel. Call once, last, on every internal page."""
    st.markdown(_CSS, unsafe_allow_html=True)
    st.session_state.setdefault("chat_history", [])
    open_ = st.session_state.setdefault("ny_chat_open", False)

    with st.container(key="ny_fab"):
        if st.button("✕" if open_ else "💬", key="ny_fab_btn",
                     help="Ask Nyaya" if not open_ else "Close"):
            st.session_state.ny_chat_open = not open_
            st.rerun()

    if not open_:
        return

    focus = _focus_case_id()
    with st.container(key="ny_panel"):
        head, clear = st.columns([2.3, 1])
        head.markdown(
            '<div class="ny-chat-head">Ask Nyaya</div>'
            f'<div class="ny-chat-sub">{"Focused on case #%d" % focus if focus else "Hindi, Hinglish or English"}'
            '</div>', unsafe_allow_html=True)
        if clear.button("Clear", key="ny_clear", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

        prompt = st.session_state.pop("ny_pending", None)
        with st.container(height=330, border=False):
            _transcript()
            if not st.session_state.chat_history and not prompt:
                st.caption("जो पूछना है, अपनी भाषा में पूछिए।")
                for i, s in enumerate(STARTERS):
                    if st.button(s, key=f"ny_starter{i}", use_container_width=True):
                        st.session_state.ny_pending = s
                        st.rerun()
            if prompt:
                _answer(prompt, focus)

        typed = st.chat_input("Ask about a case, a deadline, a fee…", key="ny_input")
        if typed:
            st.session_state.ny_pending = typed
            st.rerun()
