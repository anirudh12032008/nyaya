# Contributing to Nyaya

Everyone works on their own branch and merges through a pull request. `main` is always
demo-ready and deployed at https://nyaya.workwithani.tech, so nothing lands on it directly.

## The loop

```bash
git switch main && git pull                 # 1. start from fresh main
git switch -c feat/<short-name>             # 2. branch: feat/, fix/, docs/, data/
# ... edit ...
python -m pytest -q                         # 3. tests must pass, no API key needed
git add -A && git commit -m "Stage 5E: multi-clinic tenancy"
git push -u origin feat/<short-name>        # 4. push
gh pr create --fill                         # 5. open PR (or use the GitHub UI)
```

Then: CI runs pytest on the PR, one teammate reviews, author merges with **Squash and merge**,
delete the branch. Keep PRs small: one stage, one module, or one bug.

Branch names: `feat/voice-intake`, `fix/verifier-dates`, `docs/readme`, `data/bns-sections`.

## Keeping your branch current

```bash
git fetch origin && git rebase origin/main   # then git push --force-with-lease
```

Rebase, do not merge main into your branch. If two of you touch the same file, talk before
pushing; conflicts in `agent/prompts/*.md` are the usual case.

## Who owns what

| Area | Files | Rule |
|---|---|---|
| Model calls | `agent/client.py` | Do not change the `ask()` signature. Everything goes through it, so caching and tracing keep working. |
| Router | `app.py` | Add a page by creating `ui/<name>.py` with `render()` and adding it to `PAGES`. Never add a `pages/` dir. |
| Prompts | `agent/prompts/*.md` | Load with `agent.prompts.load(name)`. Changing a prompt changes cache keys, so re-run `warm_cache.py` before a demo. |
| Law data | `data/*.json` | Every entry needs a `source`. Schema in `CONTRACT.md`. |
| Section guard | `agent/sections.py` | Drafts may only cite IDs in the data files. Never bypass. |
| Money | `agent/forum.py` | Forum, fee, limitation are computed in Python and passed to the model as text. |
| DB | `db/db.py`, `db/schema.sql` | Schema change = migration note in the PR. `db/nyaya.db` is gitignored. |
| Hooks | `ui/hooks.py` | Intake and admin extensions plug in here. See "How it works" in the README. |

## Tests

Every test runs offline. Monkeypatch the model:

```python
def test_x(monkeypatch):
    monkeypatch.setattr(client, "ask", lambda *a, **k: '{"module": "consumer", ...}')
```

Tests are grouped per stage (`tests/test_stage4.py`). Add yours to the stage you touched.

## Commits

Short imperative subject with the stage or module up front. Examples from history:

```
Stage 4 + 5B, wire hooks, launchd + Cloudflare tunnel deploy
Hide language markers in public guide
```
