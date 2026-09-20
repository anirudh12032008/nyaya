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
    "Document analyzer": ("🔍", document_analyzer),
    "Guided tour": ("🧭", tour),
}


def _masthead() -> None:
    st.sidebar.markdown(
        '<div class="ny-brand"><div class="ny-seal">⚖</div><div>'
        f'<div style="font-family:\'Source Serif 4\',Georgia,serif;font-size:1.3rem;'
        f'font-weight:700;line-height:1.05;color:{theme.NAVY}">NYAYA <span style="font-size:.95rem;'
        f'color:{theme.BRASS}">न्याय</span></div>'
        f'<div style="font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;'
        f'color:{theme.MUTED};font-weight:700">AI for people\'s justice</div>'
        '</div></div>', unsafe_allow_html=True)


def _urgent_count() -> int:
    """Open cases inside ten days of limitation, for the badge on the Cases row."""
    try:
        from db import db
        return sum(1 for c in db.list_cases()
                   if c.get("status") not in ("filed", "closed")
                   and (d := db.days_to_deadline(c.get("deadline"))) is not None and d < 10)
    except Exception:
        return 0


def _nav() -> str:
    """Sidebar nav as a list of rows. The current row is the filled one."""
    current = st.session_state.pop("_nav", None) or st.session_state.get("nav_page") \
        or ("Cases" if st.query_params.get("case") else "Home")
    if current not in PAGES:
        current = "Home"
    st.session_state["nav_page"] = current

    urgent = _urgent_count()
    st.sidebar.markdown('<div class="ny-navlabel">Workspace</div>', unsafe_allow_html=True)
    for label, (icon, _mod) in PAGES.items():
        if label == "Guided tour":                      # help sits apart from daily work
            st.sidebar.markdown('<div class="ny-navlabel">Help</div>', unsafe_allow_html=True)
        row = f"{icon}  {label}"
        if label == "Cases" and urgent:
            row += f"   ·  {urgent} urgent"
        if st.sidebar.button(row, key=f"nav_{label}", width="stretch",
                             type="primary" if label == current else "secondary"):
            st.session_state["nav_page"] = label
            st.rerun()
    return current


def _footer() -> None:
    clinic = st.query_params.get("clinic") or "Bhopal Legal Aid Clinic"
    st.sidebar.markdown(
        f'<div class="ny-navlabel">Clinic</div>'
        f'<div class="ny-clinic"><div><span style="color:{theme.OK}">●</span> '
        f'<b style="color:{theme.INK}">{clinic}</b></div>'
        f'<div style="color:{theme.MUTED};margin-top:.1rem">Madhya Pradesh</div></div>',
        unsafe_allow_html=True)
    st.sidebar.markdown(
        f'<div style="margin-top:1.1rem;border-left:3px solid {theme.BRASS};padding-left:.7rem;'
        f'font-family:\'Source Serif 4\',Georgia,serif;color:{theme.MUTED};font-size:.86rem;'
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
    chat.render_dock()
elif qp.get("case") and qp.get("view") == "readonly":           # stage4: shared read-only case
    from ui import stage4
    stage4.render_readonly(qp["case"])
else:
    _masthead()
    # pages hand the nav over by setting st.session_state["_nav"] = "Cases" before a rerun
    choice = _nav()
    _footer()
    PAGES[choice][1].render()
    chat.render_dock()
