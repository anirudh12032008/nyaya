"""Guided tour: script stays in sync with the real pages, prompt is grounded — no API key needed."""
import re
from pathlib import Path

from agent import client, tour

ROOT = Path(__file__).resolve().parent.parent


def _app_pages():
    """The page labels app.py actually routes to, read as text so importing streamlit isn't needed."""
    src = re.search(r"PAGES = \{(.*?)\}", ROOT.joinpath("app.py").read_text(), re.S).group(1)
    return set(re.findall(r'"([^"]+)":', src))


def test_every_step_points_at_a_real_page():
    missing = {s["page"] for s in tour.STEPS} - _app_pages()
    assert not missing, f"tour references pages that app.py does not route to: {missing}"


def test_the_tour_is_registered_as_a_page():
    assert "Guided tour" in _app_pages()


def test_every_step_is_filled_in():
    for i, s in enumerate(tour.STEPS):
        assert {"page", "title", "do", "why"} == set(s), f"step {i} has the wrong keys"
        assert all(str(v).strip() for v in s.values()), f"step {i} has an empty field"


def test_prompt_carries_the_script_the_current_step_and_real_state(monkeypatch):
    seen = {}

    def fake_ask(model, system, user, **kw):
        seen["system"], seen["user"] = system, user
        return "ok"

    monkeypatch.setattr(client, "ask", fake_ask)
    assert tour.tour_turn([("user", "hi"), ("assistant", "hello")], "what now?", step=2) == "ok"
    assert tour.STEPS[2]["title"] in seen["system"]
    assert "step 3 of" in seen["system"]
    assert tour.STEPS[-1]["title"] in seen["system"], "whole script should be in the prompt"
    assert "hello" in seen["user"] and seen["user"].endswith("USER: what now?")


def test_step_index_is_clamped(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "ask", lambda m, s, u, **k: seen.setdefault("s", s) or "ok")
    tour.tour_turn([], "hi", step=999)
    assert f"step {len(tour.STEPS)} of {len(tour.STEPS)}" in seen["s"]
