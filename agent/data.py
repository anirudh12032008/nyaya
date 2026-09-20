"""Tiny loader for the preloaded statute JSON in data/ (owned by the data agent)."""
import json
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=None)
def load(name: str) -> dict:
    return json.loads((DIR / f"{name}.json").read_text(encoding="utf-8"))
