"""Public "how to file" guide per module: Sonnet writes EN + HI, cached in public/<module>.md."""
from __future__ import annotations

import json
from pathlib import Path

from agent import client, prompts, sections
from agent.data import load

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"

CTA = "Get help at your nearest legal aid clinic"
TITLES = {"en": "How to file a {m} complaint in Madhya Pradesh",
          "hi": "मध्य प्रदेश में {m} शिकायत कैसे दर्ज करें"}
_MARK = "<!-- nyaya:lang="


def path(module: str) -> Path:
    return PUBLIC / f"{module}.md"


def read(module: str) -> dict | None:
    """Parse a previously generated public/<module>.md back into {"en":..,"hi":..}."""
    p = path(module)
    if not p.exists():
        return None
    out = {}
    for chunk in p.read_text(encoding="utf-8").split(_MARK)[1:]:
        lang, _, body = chunk.partition("-->")
        body = body.strip()
        if body.startswith("# "):           # drop the title line _render() added back
            body = body.split("\n", 1)[1].strip() if "\n" in body else ""
        out[lang.strip()] = body
    return out or None


def _render(module: str, guide: dict) -> str:
    return "\n\n".join(
        f"{_MARK}{lang} -->\n\n# {TITLES[lang].format(m=module)}\n\n{guide.get(lang, '').strip()}"
        for lang in ("en", "hi"))


def generate(module: str, refresh: bool = False) -> dict:
    """-> {"en": md, "hi": md}, also written to public/<module>.md. Cached on disk."""
    if not refresh:
        cached = read(module)
        if cached:
            return cached

    portal = load("portals").get(module, {})
    rules = sections.entries(module)
    user = (f"Module: {module}\nState: Madhya Pradesh\n\n"
            f"Portal / filing details JSON:\n{json.dumps(portal, ensure_ascii=False, indent=1)}\n\n"
            f"Rules JSON (the ONLY ids you may cite):\n"
            f"{json.dumps(rules, ensure_ascii=False, indent=1)}\n")
    guide = client.ask(client.SONNET, prompts.load("guide"), user, json_mode=True)

    PUBLIC.mkdir(exist_ok=True)
    path(module).write_text(_render(module, guide) + "\n", encoding="utf-8")
    return {"en": guide.get("en", ""), "hi": guide.get("hi", "")}


if __name__ == "__main__":
    g = generate("consumer")
    print(f"ok, en={len(g['en'])} chars, hi={len(g['hi'])} chars -> {path('consumer')}")
