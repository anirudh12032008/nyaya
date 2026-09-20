"""Stage 2 dispatch: classification -> the police or tenant drafter, with trace."""
from __future__ import annotations

from agent import client

MODULES = ("police", "tenant")


def run_module(module: str, classification: dict, raw_text: str,
               today: str | None = None, trace: list | None = None) -> dict:
    """Draft for `module`; append one trace entry. Returns the drafter's dict."""
    facts = (classification or {}).get("facts") or {}

    if module == "police":
        from agent.police import draft_police
        out = draft_police(facts, raw_text, today)
    elif module == "tenant":
        from agent.tenant import draft_tenant
        out = draft_tenant(raw_text, facts, today)
    else:
        raise ValueError(f"pipeline_modules handles {MODULES}, not {module!r}")

    if trace is not None:
        trace.append({"step": f"draft_{module}", **client.last_trace()})
    return out
