"""Nyaya - Streamlit entry / app shell + page router."""
import streamlit as st

st.set_page_config(page_title="Nyaya · Legal aid clinic", page_icon="⚖️",
                   layout="wide", initial_sidebar_state="expanded")

from db.db import init as _db_init; _db_init()  # noqa: E402  (schema + seed, idempotent)
from ui import landing, theme  # noqa: E402

theme.apply()

from ui import admin, cases, chat, document_analyzer, home, intake, tour  # noqa: E402

# label -> (icon, module)
PAGES = {
    "Home": ("🏠", home),
    "New intake": ("📝", intake),
    "Cases": ("🗂️", cases),
    "Document analyzer": ("🔍", document_analyzer),
    "Admin": ("🛠️", admin),
    "Guided tour": ("🧭", tour),
}

# who sees what. The sidebar is grouped by role so nobody has to guess.
ROLES = {
    "Citizen":   {"blurb": "Get help with your problem",
                  "pages": ["Home", "New intake", "Document analyzer"]},
    "Volunteer / Lawyer": {"blurb": "Run intakes and manage cases",
                  "pages": ["Home", "New intake", "Cases", "Document analyzer"]},
    "Admin":     {"blurb": "Clinic head: oversight and settings",
                  "pages": ["Home", "Cases", "Admin"]},
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
    """Sidebar: pick a role, then a short list of pages for that role."""
    c1, c2 = st.sidebar.columns(2)
    c1.toggle("🌙 Night", key="night")
    c2.toggle("हिंदी", key="hindi")
    st.sidebar.markdown(f'<div class="ny-navlabel">{theme.t("I am a")}</div>', unsafe_allow_html=True)
    role = st.sidebar.selectbox("I am a", list(ROLES), key="role", label_visibility="collapsed",
                                format_func=lambda x: theme.t(x),
                                index=list(ROLES).index(st.session_state.get("role", "Citizen")))
    st.sidebar.caption(theme.t(ROLES[role]["blurb"]))
    allowed = ROLES[role]["pages"]

    current = st.session_state.pop("_nav", None) or st.session_state.get("nav_page") \
        or ("Cases" if st.query_params.get("case") else "Home")
    if current not in allowed and current != "Guided tour":
        current = "Home"
    st.session_state["nav_page"] = current

    urgent = _urgent_count()
    st.sidebar.markdown(f'<div class="ny-navlabel">{theme.t(role)}</div>', unsafe_allow_html=True)
    for label in allowed + ["Guided tour"]:
        icon = PAGES[label][0]
        if label == "Guided tour":                      # help sits apart from daily work
            st.sidebar.markdown(f'<div class="ny-navlabel">{theme.t("Help")}</div>', unsafe_allow_html=True)
        row = f"{icon}  {theme.t(label)}"
        if label == "Cases" and urgent:
            row += f"   ·  {urgent} {theme.t('urgent')}"
        if st.sidebar.button(row, key=f"nav_{label}", width="stretch",
                             type="primary" if label == current else "secondary"):
            st.session_state["nav_page"] = label
            st.rerun()
    return current


def _footer() -> None:
    clinic = st.query_params.get("clinic") or "Bhopal Legal Aid Clinic"
    st.sidebar.markdown(
        f'<div class="ny-navlabel">{theme.t("Clinic")}</div>'
        f'<div class="ny-clinic"><div><span style="color:{theme.OK}">●</span> '
        f'<b style="color:{theme.INK}">{clinic}</b></div>'
        f'<div style="color:{theme.MUTED};margin-top:.1rem">{theme.t("Madhya Pradesh")}</div></div>',
        unsafe_allow_html=True)
    st.sidebar.markdown(
        f'<div style="margin-top:1.1rem;border-left:3px solid {theme.BRASS};padding-left:.7rem;'
        f'font-family:\'Source Serif 4\',Georgia,serif;color:{theme.MUTED};font-size:.86rem;'
        f'line-height:1.45">“Nyaya for every citizen.”<br>हर नागरिक के लिए न्याय।</div>',
        unsafe_allow_html=True)

qp = st.query_params
page = qp.get("page", "")
is_direct_workspace_link = bool(qp.get("enter") or qp.get("clinic") or page or qp.get("case"))

if not is_direct_workspace_link and not st.session_state.get("landing_entered"):
    if landing.render():
        st.session_state["landing_entered"] = True
        st.session_state["_just_entered"] = True
        st.rerun()
elif page.startswith("guide-"):                                 # stage4: public how-to page
    from ui import stage4
    stage4.render_guide(page[len("guide-"):])
elif page == "admin":                                           # deep link -> admin role
    st.session_state["role"] = "Admin"; st.session_state["_nav"] = "Admin"
    st.query_params.clear(); st.rerun()
elif qp.get("case") and qp.get("view") == "readonly":           # stage4: shared read-only case
    from ui import stage4
    stage4.render_readonly(qp["case"])
else:
    if st.session_state.pop("_just_entered", False):
        theme.enter_animation()
    _masthead()
    # pages hand the nav over by setting st.session_state["_nav"] = "Cases" before a rerun
    choice = _nav()
    theme.apply()          # night-mode CSS depends on the toggle rendered above
    _footer()
    PAGES[choice][1].render()
    chat.render_dock()
