"""The Hindi toggle: lookup, fallback, and that the dict matches the real strings."""
import streamlit as st

from ui import theme
from ui.hi import HI


def test_english_by_default():
    st.session_state.clear()
    assert theme.t("Home") == "Home"
    assert theme.t("Home", "होम") == "Home"


def test_hindi_from_the_dict():
    st.session_state["hindi"] = True
    assert theme.t("Home") == "होम"
    st.session_state.clear()


def test_explicit_hindi_wins_over_the_dict():
    st.session_state["hindi"] = True
    assert theme.t("Home", "गृह") == "गृह"
    st.session_state.clear()


def test_missing_key_falls_back_to_english():
    st.session_state["hindi"] = True
    assert theme.t("Not a key in the dict") == "Not a key in the dict"
    st.session_state.clear()


def test_deadline_badge_keeps_the_number():
    """The count is interpolated, so a bad template would drop or double it."""
    st.session_state["hindi"] = True
    assert "9" in theme.deadline_badge(9)
    assert "दिन बचे" in theme.deadline_badge(9)
    assert "3" in theme.deadline_badge(-3)
    st.session_state.clear()


def test_every_value_is_devanagari():
    """A key accidentally mapped to English would silently do nothing."""
    for en, hi in HI.items():
        assert any("ऀ" <= ch <= "ॿ" for ch in hi), f"no Devanagari for {en!r}"


def test_format_keys_keep_their_placeholder():
    for en, hi in HI.items():
        assert en.count("%d") == hi.count("%d"), f"placeholder mismatch for {en!r}"
