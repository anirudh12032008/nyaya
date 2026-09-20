## What
<!-- one or two lines: what changed and why -->

## Where
<!-- which stage / module: agent/, ui/, db/, pdf/, data/, agent/prompts/ -->

## Checklist
- [ ] `python -m pytest -q` passes locally
- [ ] New logic has a test in `tests/` that runs without an API key (monkeypatch `agent.client.ask`)
- [ ] Money / forum / fee / deadline still computed in Python, never by the model
- [ ] New section IDs go through the `agent/sections.py` guard
- [ ] Prompts changed? List them:
- [ ] README / CONTRACT.md updated if a shared interface changed
