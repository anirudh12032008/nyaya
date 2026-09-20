# Nyaya build contract (all agents read this first)

Spec: /Users/anirudh/Downloads/nyaya-claude-code-prompt.md  (read it fully).
Python: `.venv/bin/python` (3.12; deps installed). Run streamlit with `.venv/bin/streamlit run app.py`.
No ANTHROPIC_API_KEY in this environment: code must run end-to-end with the cache/fallback path; write unit checks that do NOT need the API (monkeypatch `agent.client.ask`).

## Shared modules (do not rewrite; extend only if you own them)
- `agent/client.py`: `ask(model, system, user, json_mode=False, temperature=0.0, max_tokens=4096)`; constants `HAIKU`, `SONNET`; `last_trace()` -> {"model","ms","cached"}. Caches by sha256 to `cache/`.
- `app.py`: router. Pages live in `ui/<name>.py`, each exposes `render()`. Do NOT add a `pages/` dir (Streamlit hijacks it).
- Prompts: `agent/prompts/<name>.md`, loaded via `agent/prompts.py:load(name)` (Stage 1 agent creates this helper; others use it).
- Trace: every pipeline step appends `{"step": str, "model": str, "ms": int, "cached": bool}` to a list returned alongside results.

## Data file schemas (owned by DATA agent; consumers code against these)
- `data/cpa_rules.json`: `{"forums":[{"id":"district","name":"District Commission","min_inr":0,"max_inr":5000000,"source":...}, state 5000000-20000000, national >20000000], "fee_slabs":[{"max_inr":500000,"fee_inr":0,...},...], "limitation":{"years":2,"section":"69"}, "sections":[{"id":"2(7)","title":"consumer","gist":"...","source":"Consumer Protection Act 2019"}, ...]}`
- `data/portals.json`: `{"consumer":{"portal_url":"https://edaakhil.nic.in","documents":[...],"fee_rule":"...","deadline_rule":"2 years from cause of action"}, "police":{...}, "tenant":{...}}`
- `data/bns_sections.json`: `{"sections":[{"id":"303","act":"BNS 2023","title":"Theft","gist":"...","punishment":"...","cognizable":true,"ipc_equivalent":"378/379"}, ..., {"id":"BNSS 173","act":"BNSS 2023",...}, {"id":"IT Act 66C",...}]}`
- `data/tenancy_rules.json`: `{"rules":[{"id":"REG-17","title":"...","gist":"...","source":"Registration Act 1908 s.17","severity":"high"}, ...]}`
- `data/nalsa_eligibility.json`: `{"categories":[{"id":"sc_st","label":"...","source":"LSA Act 1987 s.12(a)"},...], "income_ceiling_inr":{"mp":300000, "supreme_court":500000}}`
- `data/seed_cases.json`: list of 12 case dicts matching `cases` table columns (see schema below) minus id/created_at, with `deadline` as ISO date.

## Section-ID guard (hard rule)
`agent/sections.py:valid_ids(module) -> set[str]` and `filter_sections(module, sections) -> (kept, dropped)`. Every drafter must call it and log dropped ids. Stage 1 agent creates this.

## Money is computed in Python, never by the model
`agent/forum.py:compute(amount_inr) -> {"forum": str, "forum_id": str, "fee_inr": int, "limitation_years": 2}` from cpa_rules.json. Stage 1 agent creates it; drafts receive forum+fee as input text.

## DB (Stage 3 agent) — schema.sql exactly:
cases(id INTEGER PK, created_at TEXT, module TEXT, status TEXT, urgency TEXT, client_name TEXT, summary TEXT, draft_md TEXT, sections_json TEXT, deadline TEXT, assigned_to INTEGER, eligible_aid INTEGER, eligibility_reason TEXT, intake_seconds REAL, trace_json TEXT, facts_json TEXT)
volunteers(id, name, load)
feedback(id, case_id, rating, note, created_at)
events(id, case_id, type, payload, ts)
`db/db.py`: `connect()`, `init()` (creates + seeds on first run), `create_case(dict)->id`, `list_cases(filters)`, `get_case(id)`, `update_case(id, **fields)`, `add_feedback`, `log_event`, `stats()`.

## Pipeline entry (Stage 1 agent creates, others extend)
`agent/pipeline.py:run_intake(text, module_override=None) -> dict` with keys: classification, forum (if consumer), draft (dict per spec), trace (list), sections_dropped. Stage 2 adds police/tenant branches; Stage 3 wraps it to persist a case.
