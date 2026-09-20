"""Guided tour page: step through the app, ask the guide anything about it."""
import streamlit as st

from agent.tour import STEPS, tour_turn

ASKS = ["What does this page do?", "Mujhe pehle kya karna chahiye?",
        "What is the difference between the council and Ask Nyaya?"]


def _go(i):
    st.session_state.tour_step = max(0, min(i, len(STEPS) - 1))


def render():
    st.title("🧭 Guided tour")
    st.caption("A walkthrough of Nyaya, in the order you would actually use it. "
               "Ask the guide anything about the app at the bottom.")
    st.session_state.setdefault("tour_step", 0)
    st.session_state.setdefault("tour_chat", [])

    i = st.session_state.tour_step
    step = STEPS[i]
    st.progress((i + 1) / len(STEPS), text=f"Step {i + 1} of {len(STEPS)}")

    st.subheader(f"{step['page']} · {step['title']}")
    st.markdown(f"**Do this:** {step['do']}")
    st.info(step["why"])

    a, b, c = st.columns([1, 1, 2])
    a.button("← Back", disabled=i == 0, on_click=_go, args=(i - 1,), use_container_width=True)
    b.button("Next →", disabled=i == len(STEPS) - 1, on_click=_go, args=(i + 1,),
             type="primary", use_container_width=True)
    if i == len(STEPS) - 1:
        c.success("That is the whole app. Pick any page in the sidebar to start.")

    with st.sidebar:
        st.caption("Jump to a step")
        for n, s in enumerate(STEPS):
            st.button(f"{n + 1}. {s['title']}", key=f"tourjump{n}", on_click=_go, args=(n,),
                      use_container_width=True)

    st.divider()
    for role, text in st.session_state.tour_chat:
        st.chat_message(role).markdown(text)

    prompt = st.chat_input("Ask about the app — a page, a button, what to do next…")
    if not prompt and not st.session_state.tour_chat:
        cols = st.columns(len(ASKS))
        for n, s in enumerate(ASKS):
            if cols[n].button(s, key=f"tourask{n}", use_container_width=True):
                prompt = s
    if not prompt:
        return

    st.chat_message("user").markdown(prompt)
    with st.chat_message("assistant"):
        try:
            with st.spinner("…"):
                reply = tour_turn(st.session_state.tour_chat, prompt, step=i)
        except Exception as e:
            st.error(f"The guide could not answer: {e}")
            return
        st.markdown(reply)
    st.session_state.tour_chat += [("user", prompt), ("assistant", reply)]
