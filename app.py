"""Nyaya - Streamlit entry / app shell + page router."""
import streamlit as st

st.set_page_config(page_title="Nyaya · Legal aid clinic", page_icon="⚖️",
                   layout="wide", initial_sidebar_state="expanded")

from db.db import init as _db_init; _db_init()  # noqa: E402  (schema + seed, idempotent)
from ui import theme  # noqa: E402

theme.apply()

from ui import admin, cases, chat, document_analyzer, home, intake, tour  # noqa: E402

# label -> (icon, module). Admin stays off the sidebar, reachable at ?page=admin.
PAGES = {
    "Home": ("🏠", home),
    "New intake": ("📝", intake),
    "Cases": ("🗂️", cases),
    "Ask Nyaya": ("💬", chat),
    "Document analyzer": ("🔍", document_analyzer),
    "Guided tour": ("🧭", tour),
}


def _masthead() -> None:
    st.sidebar.markdown(
        '<div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.2rem">'
        '<div style="font-size:1.6rem">⚖️</div><div>'
        f'<div style="font-family:\'Source Serif 4\',Georgia,serif;font-size:1.35rem;'
        f'font-weight:700;line-height:1;color:{theme.NAVY}">NYAYA <span style="font-size:1rem;'
        f'color:{theme.BRASS}">न्याय</span></div>'
        f'<div style="font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;'
        f'color:{theme.MUTED};font-weight:600">AI for people\'s justice</div>'
        '</div></div><hr style="margin:.7rem 0">', unsafe_allow_html=True)


def _footer() -> None:
    st.sidebar.markdown("<hr style='margin:.9rem 0'>", unsafe_allow_html=True)
    clinic = st.query_params.get("clinic") or "Bhopal Legal Aid Clinic"
    st.sidebar.markdown(
        f'<div style="font-size:.8rem;color:{theme.MUTED}">'
        f'<div><span style="color:{theme.OK}">●</span> '
        f'<b style="color:{theme.INK}">{clinic}</b></div>'
        f'<div style="margin-top:.15rem">Madhya Pradesh</div></div>', unsafe_allow_html=True)
    st.sidebar.markdown(
        f'<div style="margin-top:1rem;border-left:3px solid {theme.BRASS};padding-left:.7rem;'
        f'font-family:\'Source Serif 4\',Georgia,serif;color:{theme.MUTED};font-size:.88rem;'
        f'line-height:1.45">“Nyaya for every citizen.”<br>हर नागरिक के लिए न्याय।</div>',
        unsafe_allow_html=True)

qp = st.query_params
page = qp.get("page", "")

if page.startswith("guide-"):                                   # stage4: public how-to page
    from ui import stage4
    stage4.render_guide(page[len("guide-"):])
elif page == "admin":                                           # hidden from the sidebar
    _masthead()
    st.sidebar.caption("Admin · clinic head")
    admin.render()
    _footer()
elif qp.get("case") and qp.get("view") == "readonly":           # stage4: shared read-only case
    from ui import stage4
    stage4.render_readonly(qp["case"])
else:
    _masthead()
    # pages can hand the nav over by setting st.session_state["_nav"] = "Cases" before a rerun
    default = st.session_state.pop("_nav", None) or ("Cases" if qp.get("case") else "Home")
    if default not in PAGES:
        default = "Home"
    choice = st.sidebar.radio("Navigate", list(PAGES), index=list(PAGES).index(default),
                              format_func=lambda k: f"{PAGES[k][0]}  {k}",
                              label_visibility="collapsed")
    _footer()
    PAGES[choice][1].render()
