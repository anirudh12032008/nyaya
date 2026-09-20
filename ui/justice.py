"""Justice theme: a photoreal 3D emblem, and the agent bot's icon.

The model is loaded from a URL you host, not from the repo, so no binary lands in git.
Set it once with NYAYA_JUSTICE_MODEL_URL, or paste one on the page to try it.

Rendering is Google's <model-viewer> web component, embedded in Streamlit's iframe.
It is the boring choice on purpose: one pinned script tag gets PBR materials, image-based
lighting, contact shadows, orbit controls and WebXR, with no build step and no three.js
scene for anyone to maintain.
"""
from __future__ import annotations

import html
import os
from urllib.parse import urlparse

import streamlit as st

# Pinned, not floating: a CDN dependency that silently upgrades is a demo that breaks live.
VIEWER_JS = "https://cdn.jsdelivr.net/npm/@google/model-viewer@4.0.0/dist/model-viewer.min.js"
MODEL_URL = os.getenv("NYAYA_JUSTICE_MODEL_URL", "")
AVATAR_URL = os.getenv("NYAYA_JUSTICE_AVATAR_URL", "")
FALLBACK_AVATAR = "⚖️"
SUFFIXES = (".glb", ".gltf")


def safe_url(url: str) -> str:
    """Whitelist http(s) before the URL is written into the iframe's HTML.

    The value can arrive from a deploy-time env var or a text box, and it lands in a
    src attribute, so `javascript:` and `data:` have to be rejected here rather than
    relied on to be harmless later.
    """
    url = (url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("The model URL must be an http:// or https:// link.")
    return url


def bot_avatar() -> str:
    """The agent's chat icon: a still of the statue if one is configured, else the scales.

    st.chat_message takes an image URL or an emoji, so a render of the model stands in
    for the model — a <model-viewer> cannot live inside a chat avatar.
    """
    try:
        return safe_url(st.session_state.get("justice_avatar_url", AVATAR_URL)) or FALLBACK_AVATAR
    except ValueError:
        return FALLBACK_AVATAR


def viewer_html(url: str, *, exposure: float = 1.0, auto_rotate: bool = True,
                height: int = 620) -> str:
    """The <model-viewer> document. url must already have passed safe_model_url()."""
    src = html.escape(url, quote=True)
    return f"""<!doctype html>
<meta charset="utf-8">
<script type="module" src="{VIEWER_JS}"></script>
<style>
  html, body {{ margin: 0; background: transparent; }}
  model-viewer {{
    width: 100%; height: {height}px;
    /* the plinth the statue stands on: a soft pool of light in a dark room */
    background: radial-gradient(ellipse at 50% 78%, #3b3b40 0%, #212124 45%, #141416 100%);
    border: 1px solid rgba(201, 162, 39, .35);
    border-radius: 14px;
    --poster-color: transparent;
    --progress-bar-color: #c9a227;
    --progress-mask: transparent;
  }}
  .err {{
    display: none; position: absolute; inset: auto 0 18px 0; text-align: center;
    color: #e6b8b8; font: 14px/1.5 system-ui, sans-serif;
  }}
</style>
<model-viewer
  src="{src}"
  alt="A three-dimensional statue of Lady Justice, blindfolded, holding scales and a sword"
  camera-controls
  {"auto-rotate" if auto_rotate else ""}
  auto-rotate-delay="600"
  rotation-per-second="18deg"
  interaction-prompt="auto"
  environment-image="neutral"
  tone-mapping="aces"
  exposure="{exposure:.2f}"
  shadow-intensity="1.15"
  shadow-softness="0.75"
  min-field-of-view="18deg"
  max-field-of-view="55deg"
  touch-action="pan-y">
  <div class="err" id="err">The model could not be loaded from that URL.</div>
</model-viewer>
<script type="module">
  const mv = document.querySelector('model-viewer');
  mv.addEventListener('error', () => {{ document.getElementById('err').style.display = 'block'; }});
</script>
"""


def render():
    st.title("⚖️ Justice")
    st.caption("The clinic's emblem in 3D — drag to orbit, scroll to zoom, double-click to recentre.")

    url = st.session_state.get("justice_model_url", MODEL_URL)

    if not url:
        st.info(
            "**No model is configured yet.** Host a `.glb` or `.gltf` anywhere that serves it "
            "over https with CORS enabled — object storage, a CDN, or a GitHub release asset — "
            "then set `NYAYA_JUSTICE_MODEL_URL` in `.env`, or paste the link below to try one."
        )

    with st.expander("Model source", expanded=not url):
        typed = st.text_input(
            "URL of a .glb or .gltf", value=url,
            placeholder="https://example.com/lady-justice.glb",
            help="Stored for this session only. Set NYAYA_JUSTICE_MODEL_URL to make it stick.")
        icon = st.text_input(
            "Agent bot icon", value=st.session_state.get("justice_avatar_url", AVATAR_URL),
            placeholder="https://example.com/lady-justice.png",
            help="A still PNG of the statue, used as the agent's chat avatar on Ask Nyaya. "
                 "Blank falls back to the scales emoji. Set NYAYA_JUSTICE_AVATAR_URL to make it stick.")
        if icon != st.session_state.get("justice_avatar_url", AVATAR_URL):
            st.session_state.justice_avatar_url = icon
            st.rerun()
        st.chat_message("assistant", avatar=bot_avatar()).caption("This is how the agent will look.")
        if typed != url:
            st.session_state.justice_model_url = typed
            st.rerun()
        if url and not url.lower().endswith(SUFFIXES):
            st.warning("That link does not end in .glb or .gltf — model-viewer may refuse it.")

    if not url:
        return

    try:
        src = safe_url(url)
    except ValueError as e:
        st.error(str(e))
        return

    a, b = st.columns([1, 2])
    spin = a.toggle("Auto-rotate", value=True)
    # Materials are authored against an exposure the app cannot know; leave the knob.
    exposure = b.slider("Lighting", 0.4, 2.0, 1.0, 0.05,
                        help="Marble and gold need different exposure — tune until it looks right.")

    st.components.v1.html(viewer_html(src, exposure=exposure, auto_rotate=spin), height=650)
    st.caption("Renders with WebGL in your browser. The model is fetched from the URL above, "
               "never stored in the repo.")
