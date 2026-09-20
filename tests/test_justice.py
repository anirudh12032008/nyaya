"""Justice 3D page: only http(s) reaches the iframe, and the URL is escaped into the HTML."""
import re
from pathlib import Path

import pytest

from ui import justice

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "ftp://example.com/statue.glb",
    "/models/statue.glb",          # relative: no scheme, no host
    "https:///statue.glb",         # scheme but no host
])
def test_only_http_urls_are_accepted(url):
    with pytest.raises(ValueError):
        justice.safe_url(url)


def test_good_urls_survive_and_blank_is_blank():
    assert justice.safe_url("  https://cdn.example.com/lady-justice.glb  ") == \
        "https://cdn.example.com/lady-justice.glb"
    assert justice.safe_url("http://localhost:8000/a.gltf").startswith("http://")
    assert justice.safe_url("") == "" and justice.safe_url(None) == ""


def test_url_is_escaped_so_it_cannot_break_out_of_the_src_attribute():
    hostile = 'https://x.test/a.glb?q="><img src=x onerror=alert(1)>'
    out = justice.viewer_html(justice.safe_url(hostile))
    assert "onerror=alert(1)>" not in out
    assert "&quot;&gt;&lt;img" in out


def test_viewer_html_carries_the_realism_settings():
    out = justice.viewer_html("https://x.test/a.glb", exposure=1.4, auto_rotate=False)
    assert 'exposure="1.40"' in out
    assert "auto-rotate\n" not in out, "auto-rotate should be off when not requested"
    for attr in ("camera-controls", "environment-image", "shadow-intensity", "tone-mapping"):
        assert attr in out
    assert "@google/model-viewer@4." in out, "the CDN version must stay pinned"


def test_avatar_falls_back_to_the_scales_when_unset_or_hostile(monkeypatch):
    monkeypatch.setattr(justice, "AVATAR_URL", "")
    assert justice.bot_avatar() == justice.FALLBACK_AVATAR
    monkeypatch.setattr(justice, "AVATAR_URL", "javascript:alert(1)")
    assert justice.bot_avatar() == justice.FALLBACK_AVATAR
    monkeypatch.setattr(justice, "AVATAR_URL", "https://x.test/statue.png")
    assert justice.bot_avatar() == "https://x.test/statue.png"


def test_the_page_is_registered_and_the_agent_uses_the_icon():
    src = re.search(r"PAGES = \{(.*?)\}", ROOT.joinpath("app.py").read_text(), re.S).group(1)
    assert "Justice" in set(re.findall(r'"([^"]+)":', src))
    chat = ROOT.joinpath("ui/chat.py").read_text()
    assert chat.count('st.chat_message("assistant", avatar=bot_avatar())') == 2, \
        "both the replayed transcript and the live reply should show the agent's icon"
