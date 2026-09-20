"""Guided tour page: step through the app, ask the guide anything about it."""
import streamlit as st

from agent.tour import STEPS, tour_turn
from ui import theme

ASKS = ["What does this page do?", "Mujhe pehle kya karna chahiye?",
        "What is the difference between the council and Ask Nyaya?"]


def _go(i):
    st.session_state.tour_step = max(0, min(i, len(STEPS) - 1))


def _strip(i: int) -> None:
    """The steps as theme's numbered strip: done behind you, current one highlighted."""
    theme.agent_strip([{"key": str(n), "title": s["page"], "desc": s["title"]}
                       for n, s in enumerate(STEPS)],
                      active=str(i), done={str(n) for n in range(i)})


def _step_card(i: int) -> None:
    step = STEPS[i]
    with theme.card():
        st.markdown(
            f'<div class="ny-eyebrow">Step {i + 1} of {len(STEPS)}</div>'
            f'<h3 style="margin:.1rem 0 .55rem">{step["title"]}</h3>'
            f'<div class="ny-row">{theme.badge(step["page"], "info")}</div>',
            unsafe_allow_html=True)
        st.write("")
        st.markdown(f"**Do this** - {step['do']}")
        theme.quote(step["why"])


def render():
    theme.page_header(
        "Guided tour",
        "Nyaya in the order you would actually use it - then ask the guide anything.",
        hindi="नए स्वयंसेवक? यहाँ से शुरू करें।",
        eyebrow="Nyaya · walkthrough",
    )
    st.session_state.setdefault("tour_step", 0)
    st.session_state.setdefault("tour_chat", [])

    i = st.session_state.tour_step
    _strip(i)
    st.write("")
    _step_card(i)

    a, b, c = st.columns([1, 1, 3])
    a.button("← Back", disabled=i == 0, on_click=_go, args=(i - 1,), use_container_width=True)
    b.button("Next →", disabled=i == len(STEPS) - 1, on_click=_go, args=(i + 1,),
             type="primary", use_container_width=True)
    if i == len(STEPS) - 1:
        c.markdown('<div class="ny-row" style="height:100%;align-items:center">'
                   + theme.badge("That is the whole app - pick any page in the sidebar", "ok")
                   + "</div>", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<div class="ny-eyebrow" style="margin-top:.7rem">Jump to a step</div>',
                    unsafe_allow_html=True)
        for n, s in enumerate(STEPS):
            st.button(f"{n + 1}.  {s['title']}", key=f"tourjump{n}", on_click=_go, args=(n,),
                      type="primary" if n == i else "secondary", use_container_width=True)

    st.write("")
    theme.section("Ask the guide",
                  "About the app itself - a page, a button, what to do next. "
                  "Questions about a case go to the 💬 bubble, bottom-right.")
    with theme.card():
        for role, text in st.session_state.tour_chat:
            st.chat_message(role, avatar=theme.AVATARS[role]).markdown(text)

        prompt = st.chat_input("Ask about the app…", key="tour_input")
        if not prompt and not st.session_state.tour_chat:
            cols = st.columns(len(ASKS))
            for n, s in enumerate(ASKS):
                if cols[n].button(s, key=f"tourask{n}", use_container_width=True):
                    prompt = s
        if not prompt:
            return

        st.chat_message("user", avatar=theme.AVATARS["user"]).markdown(prompt)
        with st.chat_message("assistant", avatar=theme.AVATARS["assistant"]):
            try:
                with st.spinner("…"):
                    reply = tour_turn(st.session_state.tour_chat, prompt, step=i)
            except Exception as e:
                st.error(f"The guide could not answer: {e}")
                return
            st.markdown(reply)
        st.session_state.tour_chat += [("user", prompt), ("assistant", reply)]
