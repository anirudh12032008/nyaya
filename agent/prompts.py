"""System prompts live in agent/prompts/<name>.md."""
from pathlib import Path

DIR = Path(__file__).resolve().parent / "prompts"


def load(name: str) -> str:
    return (DIR / f"{name}.md").read_text(encoding="utf-8")
