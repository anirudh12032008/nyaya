"""Nyaya design system: one stylesheet + a handful of HTML helpers.

Audience: legal-aid clinic volunteers, paralegals and law students in Madhya
Pradesh, working bilingually (Hindi / English) on deadline-driven case files,
often on cheap laptops in bright rooms. So: light paper background, high
contrast, big readable type, Devanagari-safe font stack, calm institutional
colours, status that reads at a glance.

Every page calls theme.apply() once (app.py does it) and then composes with
these helpers instead of hand-rolling CSS.
"""
from __future__ import annotations

import html
from contextlib import contextmanager

import streamlit as st

# ── tokens ──────────────────────────────────────────────────────────────────
INK = "#1A1D21"
MUTED = "#5B6470"
LINE = "#E4E0D7"
PAPER = "#FBFAF7"
SURFACE = "#FFFFFF"
NAVY = "#1F3A5F"       # primary: seals, headers, buttons
BRASS = "#B07D2B"      # accent: court/brass, highlights
OK = "#1B7F5A"
WARN = "#B3761A"
DANGER = "#B3261E"

TONES = {"ok": OK, "warn": WARN, "danger": DANGER, "info": NAVY, "muted": MUTED,
         "accent": BRASS}

# Streamlit's default chat avatars come from an icon font that renders as clipped
# letter boxes until it loads (very visible over the tunnel). Emoji need no font.
AVATARS = {"user": "🧑", "assistant": "⚖️"}

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap');

:root {{
  --nyaya-ink: {INK}; --nyaya-muted: {MUTED}; --nyaya-line: {LINE};
  --nyaya-paper: {PAPER}; --nyaya-surface: {SURFACE};
  --nyaya-navy: {NAVY}; --nyaya-brass: {BRASS};
  --nyaya-ok: {OK}; --nyaya-warn: {WARN}; --nyaya-danger: {DANGER};
}}

html, body, [class*="st-"], .stMarkdown, button, input, textarea, select {{
  font-family: 'Inter', 'Noto Sans Devanagari', system-ui, -apple-system, sans-serif;
}}
/* Streamlit's Material Symbols spans carry st-emotion-* classes, so the rule above
   matches them and the ligature renders as raw text ("keyboard_double_arrow_left").
   Hand the icon font back. */
[data-testid^="stIconMaterial"], .material-symbols-rounded, .material-icons {{
  font-family: 'Material Symbols Rounded' !important;
}}
.stApp {{ background: var(--nyaya-paper); color: var(--nyaya-ink); }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1380px; }}

/* headings read as documents, not dashboards */
h1, h2, h3 {{ font-family: 'Source Serif 4', Georgia, serif; letter-spacing: -.01em;
              color: var(--nyaya-ink); }}
h1 {{ font-size: 2.0rem; font-weight: 700; }}
h2 {{ font-size: 1.35rem; font-weight: 600; margin-top: .4rem; }}
h3 {{ font-size: 1.1rem; font-weight: 600; }}

/* sidebar: the clinic's masthead */
section[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, #FFFFFF 0%, #FCFAF6 100%);
  border-right: 1px solid var(--nyaya-line);
}}
section[data-testid="stSidebar"] .block-container {{ padding: 1.4rem 1rem 1.2rem; }}
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: .15rem; }}

/* nav rows: full-width buttons that read as a list, not as controls */
section[data-testid="stSidebar"] .stButton > button {{
  width: 100%; justify-content: flex-start; text-align: left;
  border: 1px solid transparent; background: transparent; color: var(--nyaya-ink);
  font-weight: 600; font-size: .92rem; padding: .48rem .65rem; border-radius: 9px;
}}
section[data-testid="stSidebar"] .stButton > button > div,
section[data-testid="stSidebar"] .stButton > button p {{
  width: 100%; text-align: left; justify-content: flex-start;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
  background: #F3F0E9; border-color: var(--nyaya-line); color: var(--nyaya-navy);
}}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
  background: {NAVY}; border-color: {NAVY}; color: #fff;
  box-shadow: 0 1px 2px rgba(31,58,95,.25);
}}
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
  background: #16293F; color: #fff;
}}
.ny-navlabel {{ font-size: .68rem; font-weight: 700; letter-spacing: .12em;
                text-transform: uppercase; color: {MUTED}; opacity: .75;
                margin: 1rem 0 .3rem .65rem; }}
/* st's markdown wrapper has margin-bottom:-1rem to cancel a trailing <p>; a bare div has none,
   so the label spilled into the next nav row. */
[data-testid="stMarkdownContainer"]:has(> .ny-navlabel) {{ margin-bottom: 0; }}
.ny-brand {{ display: flex; align-items: center; gap: .6rem; margin-bottom: 1.2rem; }}
.ny-seal {{ width: 34px; height: 34px; border-radius: 9px; flex: none;
            background: linear-gradient(140deg, {NAVY}, #2E5686);
            color: #fff; display: flex; align-items: center; justify-content: center;
            font-size: 1.1rem; box-shadow: 0 1px 3px rgba(31,58,95,.3); }}
.ny-clinic {{ border: 1px solid var(--nyaya-line); border-radius: 10px;
              padding: .55rem .65rem; background: {SURFACE}; font-size: .8rem; }}

/* controls */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
  border-radius: 8px; font-weight: 600; border: 1px solid var(--nyaya-line);
  padding: .45rem .95rem; transition: none;
}}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {{
  background: var(--nyaya-navy); border-color: var(--nyaya-navy); color: #fff;
}}
.stButton > button[kind="primary"]:hover {{ background: #16293F; border-color: #16293F; }}
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div, .stNumberInput input {{
  border-radius: 8px !important; border-color: var(--nyaya-line) !important;
  background: var(--nyaya-surface) !important; font-size: .95rem;
}}
.stTextArea textarea {{ line-height: 1.55; }}

/* tabs */
.stTabs [data-baseweb="tab-list"] {{ gap: .25rem; border-bottom: 1px solid var(--nyaya-line); }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; color: var(--nyaya-muted); padding: .5rem .85rem; }}
.stTabs [aria-selected="true"] {{ color: var(--nyaya-navy); }}

/* bordered containers become cards */
div[data-testid="stVerticalBlockBorderWrapper"] {{
  background: var(--nyaya-surface); border-radius: 12px; border-color: var(--nyaya-line);
  box-shadow: 0 1px 2px rgba(26,29,33,.04);
}}
div[data-testid="stMetric"] {{
  background: var(--nyaya-surface); border: 1px solid var(--nyaya-line);
  border-radius: 12px; padding: .85rem 1rem;
}}
div[data-testid="stMetricLabel"] p {{ color: var(--nyaya-muted); font-weight: 600;
  font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; }}

div[data-testid="stExpander"] details {{
  border: 1px solid var(--nyaya-line); border-radius: 10px; background: var(--nyaya-surface);
}}
div[data-testid="stDataFrame"] {{ border: 1px solid var(--nyaya-line); border-radius: 10px; }}
hr {{ border-color: var(--nyaya-line); }}

/* ── helper components ── */
.ny-head {{ display:flex; align-items:flex-end; justify-content:space-between; gap:1rem;
            border-bottom:1px solid var(--nyaya-line); padding-bottom:.7rem; margin-bottom:1.1rem; }}
.ny-head h1 {{ margin:0 0 .15rem 0; }}
.ny-head .sub {{ color:var(--nyaya-muted); font-size:.92rem; }}
.ny-head .hi {{ color:var(--nyaya-muted); font-size:.9rem; }}
.ny-eyebrow {{ text-transform:uppercase; letter-spacing:.09em; font-size:.72rem;
               font-weight:700; color:var(--nyaya-brass); margin-bottom:.15rem; }}

.ny-badge {{ display:inline-block; padding:.12rem .55rem; border-radius:999px;
             font-size:.75rem; font-weight:600; line-height:1.5; white-space:nowrap;
             border:1px solid currentColor; }}
.ny-badge.solid {{ border-color:transparent; }}

.ny-stat {{ background:var(--nyaya-surface); border:1px solid var(--nyaya-line);
            border-radius:12px; padding:.9rem 1rem; height:100%; }}
.ny-stat .lbl {{ font-size:.72rem; font-weight:700; letter-spacing:.06em;
                 text-transform:uppercase; color:var(--nyaya-muted); }}
.ny-stat .val {{ font-family:'Source Serif 4',Georgia,serif; font-size:1.9rem;
                 font-weight:700; line-height:1.15; margin-top:.15rem; }}
.ny-stat .dlt {{ font-size:.8rem; font-weight:600; }}

.ny-strip {{ display:flex; gap:.4rem; flex-wrap:wrap; align-items:stretch; }}
.ny-step {{ flex:1 1 0; min-width:104px; background:var(--nyaya-surface);
            border:1px solid var(--nyaya-line); border-radius:10px; padding:.6rem .7rem; }}
.ny-step.on {{ border-color:var(--nyaya-navy); box-shadow:inset 3px 0 0 var(--nyaya-navy); }}
.ny-step.done {{ background:#F4F8F5; border-color:#CBE3D6; }}
.ny-step .n {{ font-size:.68rem; font-weight:700; color:var(--nyaya-brass);
               letter-spacing:.08em; }}
.ny-step .t {{ font-weight:600; font-size:.9rem; margin-top:.1rem; }}
.ny-step .d {{ font-size:.76rem; color:var(--nyaya-muted); }}

.ny-quote {{ border-left:3px solid var(--nyaya-brass); padding:.2rem 0 .2rem .85rem;
             color:var(--nyaya-muted); font-family:'Source Serif 4',Georgia,serif;
             font-size:.95rem; line-height:1.5; }}

/* legal drafts: a sheet of paper, serif body */
.ny-doc {{ background:#FFFEFA; border:1px solid var(--nyaya-line); border-radius:10px;
           padding:1.5rem 1.8rem; font-family:'Source Serif 4',Georgia,serif;
           font-size:1rem; line-height:1.65; box-shadow:0 1px 3px rgba(26,29,33,.05); }}
.ny-doc h1,.ny-doc h2,.ny-doc h3 {{ font-size:1.05rem; text-align:left; }}

.ny-empty {{ border:1px dashed var(--nyaya-line); border-radius:12px; padding:2rem 1.5rem;
             text-align:center; background:var(--nyaya-surface); }}
.ny-empty .i {{ font-size:1.7rem; }}
.ny-empty .t {{ font-weight:600; margin-top:.35rem; }}
.ny-empty .b {{ color:var(--nyaya-muted); font-size:.9rem; }}

.ny-row {{ display:flex; gap:.45rem; flex-wrap:wrap; align-items:center; }}
.ny-kv {{ font-size:.85rem; color:var(--nyaya-muted); }}
.ny-kv b {{ color:var(--nyaya-ink); font-weight:600; }}
</style>
"""


def apply() -> None:
    """Inject the stylesheet. Safe to call more than once per run."""
    st.markdown(_CSS, unsafe_allow_html=True)


def _e(x) -> str:
    return html.escape(str(x)) if x is not None else ""


# ── components ──────────────────────────────────────────────────────────────
def page_header(title: str, subtitle: str = "", hindi: str = "", eyebrow: str = "") -> None:
    """Document-style page masthead. `hindi` is the Devanagari gloss shown at the right."""
    right = f'<div class="hi">{_e(hindi)}</div>' if hindi else ""
    eb = f'<div class="ny-eyebrow">{_e(eyebrow)}</div>' if eyebrow else ""
    sub = f'<div class="sub">{_e(subtitle)}</div>' if subtitle else ""
    st.markdown(f'<div class="ny-head"><div>{eb}<h1>{_e(title)}</h1>{sub}</div>{right}</div>',
                unsafe_allow_html=True)


def badge(text: str, tone: str = "muted", solid: bool = False) -> str:
    """Returns HTML - put it inside st.markdown(..., unsafe_allow_html=True) or badges()."""
    c = TONES.get(tone, MUTED)
    style = (f"background:{c};color:#fff;" if solid
             else f"background:{c}14;color:{c};border-color:{c}55;")
    return f'<span class="ny-badge{" solid" if solid else ""}" style="{style}">{_e(text)}</span>'


def badges(*items) -> None:
    """Render a row of badges: pass badge() HTML, (text, tone) tuples, or plain strings."""
    out = []
    for i in items:
        if not i:
            continue
        if isinstance(i, tuple):
            out.append(badge(*i))
        elif isinstance(i, str) and i.lstrip().startswith("<"):
            out.append(i)
        else:
            out.append(badge(str(i)))
    st.markdown(f'<div class="ny-row">{"".join(out)}</div>', unsafe_allow_html=True)


def deadline_badge(days: int | None) -> str:
    if days is None:
        return badge("no limitation date", "muted")
    if days < 0:
        return badge(f"limitation passed {abs(days)}d ago", "danger", solid=True)
    if days < 10:
        return badge(f"{days} days left", "danger", solid=True)
    if days < 30:
        return badge(f"{days} days left", "warn")
    return badge(f"{days} days left", "ok")


def stat_cards(items: list[dict], cols: int | None = None) -> None:
    """items: [{'label','value','delta'?,'tone'?}] - tone colours the delta line."""
    if not items:
        return
    for col, it in zip(st.columns(cols or len(items)), items):
        d = it.get("delta")
        dt = (f'<div class="dlt" style="color:{TONES.get(it.get("tone", "muted"), MUTED)}">'
              f'{_e(d)}</div>') if d else ""
        col.markdown(f'<div class="ny-stat"><div class="lbl">{_e(it["label"])}</div>'
                     f'<div class="val">{_e(it["value"])}</div>{dt}</div>',
                     unsafe_allow_html=True)


def agent_strip(steps: list[dict], active: str | None = None, done: set | None = None) -> None:
    """steps: [{'key','title','desc'}] - the intake → verify pipeline as a strip."""
    done = done or set()
    cells = []
    for i, s in enumerate(steps, 1):
        cls = "on" if s["key"] == active else ("done" if s["key"] in done else "")
        cells.append(f'<div class="ny-step {cls}"><div class="n">{i:02d}</div>'
                     f'<div class="t">{_e(s["title"])}</div>'
                     f'<div class="d">{_e(s.get("desc", ""))}</div></div>')
    st.markdown(f'<div class="ny-strip">{"".join(cells)}</div>', unsafe_allow_html=True)


def document(markdown_text: str) -> None:
    """Render a legal draft on a paper surface."""
    import re
    body = _e(markdown_text or "No draft.")
    body = re.sub(r"^### (.+)$", r"<h3>\1</h3>", body, flags=re.M)
    body = re.sub(r"^## (.+)$", r"<h2>\1</h2>", body, flags=re.M)
    body = re.sub(r"^# (.+)$", r"<h2>\1</h2>", body, flags=re.M)
    body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body)
    body = re.sub(r"(?m)^\s*[-*] (.+)$", r"• \1", body)
    body = body.replace("\n", "<br>")
    st.markdown(f'<div class="ny-doc">{body}</div>', unsafe_allow_html=True)


def quote(text: str) -> None:
    st.markdown(f'<div class="ny-quote">{_e(text)}</div>', unsafe_allow_html=True)


def kv(label: str, value: str) -> str:
    return f'<span class="ny-kv">{_e(label)} <b>{_e(value)}</b></span>'


def empty_state(icon: str, title: str, body: str = "") -> None:
    st.markdown(f'<div class="ny-empty"><div class="i">{_e(icon)}</div>'
                f'<div class="t">{_e(title)}</div><div class="b">{_e(body)}</div></div>',
                unsafe_allow_html=True)


@contextmanager
def card(title: str = "", caption: str = ""):
    """Bordered surface. Use as: `with theme.card("Recent cases"): ...`"""
    box = st.container(border=True)
    with box:
        if title:
            st.markdown(f"##### {title}")
        if caption:
            st.caption(caption)
        yield box


def section(title: str, caption: str = "") -> None:
    st.markdown(f"### {title}")
    if caption:
        st.caption(caption)
