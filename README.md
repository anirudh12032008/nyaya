# Nyaya · न्याय

**An AI legal aid clinic for Madhya Pradesh.** A citizen describes a problem in Hindi, Hinglish or
English. Nyaya classifies it, works out the correct forum, fee and deadline *in Python*, drafts the
filing, checks that draft with a second model pass, renders a PDF, and drops the case into a clinic
queue with a NALSA eligibility verdict and an assigned volunteer.

Four problem modules today - **consumer**, **police**, **tenant**, **labour** - plus a **document
analyzer**, an agentic **Ask Nyaya** assistant and a **guided tour** for new volunteers.

Stack: Streamlit + Anthropic API + SQLite. No other services. Live at https://nyaya.workwithani.tech.

Contributing? Read [CONTRIBUTING.md](CONTRIBUTING.md) first (branch → PR → review → squash).
Module contracts and data schemas live in [CONTRACT.md](CONTRACT.md).

## What's in the app

| Page | What it does |
|---|---|
| Home | Clinic dashboard: open cases, deadlines, throughput |
| New intake | Paste or speak the problem → classification, forum/fee, draft, verification, PDF |
| Cases | Queue with eligibility, assignment, evidence, audit trail, outcomes, counsel brief |
| Document analyzer | Upload a contract or notice → parties, dates, deadlines, risky clauses |
| Guided tour | An agent that walks a new volunteer through the workspace |
| Ask Nyaya | Floating 💬 bubble on every page: an Opus 5 tool-use loop over the live workspace |
| Admin | `?page=admin`, off the sidebar: metrics, overnight triage, deadline sentinel |

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
.venv/bin/python -m agent.client --selftest     # one Haiku call, prints latency
.venv/bin/python warm_cache.py                  # pre-cache every demo input (run before a demo)
.venv/bin/streamlit run app.py
```

Python 3.11+ (built on 3.12). Tests need no API key:

```bash
.venv/bin/python -m pytest -q
```

### Windows (PowerShell)

The commands above are for macOS/Linux. On Windows, call the venv's programs directly, so there is
nothing to activate:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
notepad .env                                        # one line: ANTHROPIC_API_KEY=sk-ant-...
.venv\Scripts\python -m agent.client --selftest     # one Haiku call: proves the key works
.venv\Scripts\python warm_cache.py                  # optional: pre-cache the demo inputs
.venv\Scripts\streamlit run app.py
.venv\Scripts\python -m pytest -q                   # tests need no key
```

- **Where the key goes.** Either a `.env` file in the project folder (git-ignored; save it as UTF-8,
  Notepad's default, because a UTF-16 "Unicode" file cannot be read) or, for one terminal only,
  `$env:ANTHROPIC_API_KEY = "sk-ant-..."`. `setx` only reaches terminals opened afterwards.
- **Restart Streamlit after adding or changing the key.** It is read once, when the app starts.
- **`Could not resolve authentication method`** on the first agent step means no key reached the app.
  Check the two points above, then restart. With no key, only requests already saved in `cache/` are
  served.

## How it works

### 1. Every model call goes through one function

`agent/client.py:ask(model, system, user, json_mode=False, ...)`. It applies a 45 s timeout, one
retry, then falls back to a file cache keyed by SHA-256 of model + system + user, written to
`cache/`. `last_trace()` reports model, latency and whether the reply was cached; the UI shows a
grey **cached** tag. Two models: Haiku for classification and cheap checks, Sonnet for drafting,
verification and briefs. Prompts are markdown files in `agent/prompts/` loaded by name.

### 2. The intake pipeline

`agent/pipeline.py:run_intake(text, module_override=None, answers=None)`:

```
text ──► classify (Haiku) ──► module? ──┬─ consumer ─► forum.compute() ─► draft_consumer (Sonnet)
                 │                      ├─ police   ─► pipeline_modules.run_module()
   missing fact? ┘ ask one question     └─ tenant   ─► pipeline_modules.run_module()
                                                                  │
                                              verify (Sonnet) ◄───┘
                                              fail? → one redraft → verify again
                                                                  │
                                              result: classification, forum, draft,
                                                      verification, trace, sections_dropped
```

Admin lives at `?page=admin` (not in the sidebar).

Two hard rules enforced in code, not prompts:

- **Money is computed in Python.** `agent/forum.py` reads `data/cpa_rules.json` and returns
  forum, fee and limitation. The model receives them as text and never calculates them.
- **Section IDs are guarded.** `agent/sections.py` drops any cited section not present in the
  data files. Dropped IDs are logged and shown in the trace.

### 3. Persistence and the clinic workspace

When a draft completes, `ui/intake.py` calls `ui/hooks.py:on_draft_complete(result)`, which runs
`agent/case_service.py:persist_intake` → `db/db.py:create_case`. Creating a case also runs NALSA
section 12 eligibility (`agent/eligibility.py`) and assigns the lowest-load volunteer. Schema is in
`db/schema.sql`; the SQLite file `db/nyaya.db` is created and seeded with 12 cases on first run.

### 4. Pages and hooks

`app.py` is the router. A page is a module in `ui/` exposing `render()`, registered in `PAGES`.
Query params select special views: `?page=guide-<module>` (public guide),
`?case=<id>&view=readonly` (share link), `?clinic=<slug>` (attribution from QR codes).

`ui/hooks.py` is the extension point. Cases and Admin pages look up `extra_case_actions` and
`admin_extras` by `getattr`, so Stage 4 and 5 features plug in without editing the core pages.

### 5. Stages (what exists)

| Stage | Feature | Entry point |
|---|---|---|
| 0 | Client wrapper, router, selftest | `agent/client.py`, `app.py` |
| 1 | Consumer complaint: intake → forum/fee → e-Daakhil-ordered draft → PDF | `agent/draft.py`, `agent/forum.py`, `pdf/render.py` |
| 2 | Police (SHO complaint, BNSS 173(4) SP letter, zero-FIR) and tenant (clause flags, counter-notice, PDF upload) | `agent/police.py`, `agent/tenant.py` |
| 3 | Clinic workspace: cases queue, eligibility, assignment, feedback, admin metrics | `ui/cases.py`, `ui/admin.py`, `db/db.py` |
| 4 | QR on PDFs, read-only share links, "use as template", public bilingual guides, feedback → `## Learned` prompt hints | `ui/stage4.py`, `pdf/qr.py`, `agent/guide.py`, `agent/learn.py` |
| 5A | Overnight triage: thread-pool re-screen of new cases + Sonnet morning brief PDF | `agent/triage.py`, `ui/triage.py` |
| 5B | Verifier agent: second pass on sections, forum/fee, placeholders, unsupported claims; one auto-redraft | `agent/verify.py` |
| 5C | Deadline sentinel: "advance clock 30 days" → Hindi reminders per affected case | `agent/sentinel.py` |
| 5D | Voice intake (browser SpeechRecognition, hi-IN) | `ui/intake_extras.py` |
| 5F | Filing autopilot preview: mock e-Daakhil form autofill, disabled Submit | `ui/intake_extras.py` |
| 5G | Similar past cases from the clinic DB (Sonnet over summaries, no vector DB) | `agent/similar.py` |
| 6 | Orchestra: five specialist agents (evidence, devil's advocate, strategy, risk, client letter) run in parallel on a case, then Opus 5 writes the counsel brief. Auto-runs after intake, on-demand from the case page, stored in `cases.council_json` | `agent/orchestra.py`, `ui/orchestra.py` |
| 7 | Ask Nyaya: agentic chatbot (Opus 5 tool-use loop) over the workspace - lists/opens cases, searches statutes, computes forum + fee, finds similar cases, runs the council, updates status | `agent/chat.py`, `ui/chat.py` (floating 💬 bubble, bottom-right of every page) |
| 8 | Labour module: unpaid wages, termination, PF/ESI, gratuity. Forum + limitation from `data/labour_rules.json` in Python; PWA s.15 claim + demand letter (Sonnet) | `agent/labour.py` |
| 9 | Evidence: Haiku checklist per module, upload photos/PDFs, Haiku vision labels each one, annexure index appended to the draft | `agent/evidence.py`, `ui/evidence.py` |
| 10 | Outcomes + volunteer copilot: record won/lost/settled, similar cases and `## Learned` use real outcomes; Opus plans call script + 3 dated next actions | `agent/copilot.py`, `ui/copilot.py` |
| 11 | Audit trail: per-case timeline, model calls, verifier verdict, council run, Haiku plain summary, PDF export for funders/DLSA. Also an Ask Nyaya tool | `agent/audit.py`, `ui/audit.py` |
| 12 | Document analyzer: upload any contract or notice, Sonnet extracts parties, dates, money, deadlines and flags one-sided clauses | `agent/document_analyzer.py`, `ui/document_analyzer.py` |
| 13 | Guided tour: an agent that walks a new volunteer through the workspace page by page | `agent/tour.py`, `ui/tour.py` |

## Layout

```
app.py              router
agent/              pipeline, drafters, verifier, data loaders, prompts/
ui/                 one module per page + hooks.py
db/                 schema.sql, db.py (SQLite)
pdf/                render.py, qr.py
data/               statutes, rules, portals, seed cases (JSON, each entry has a source)
templates/          draft skeletons per module
public/             generated guides and briefs
tests/              one file per stage, all offline
deploy/             launchd plists + install.sh
warm_cache.py       pre-runs every demo input through the pipeline
```

## Demo script

1. Intake → paste line 1 of `demo_inputs.txt` (Hinglish phone warranty). Show trace, forum = District, fee = nil, deadline Jan 2028, PDF.
2. Paste the builder case (₹65 lakh) → routes to State Commission, fee ₹2000.
3. Paste the refused-FIR bike theft → SHO complaint + SP letter under BNSS 173(4).
4. Paste `data/sample_rent_agreement.txt` → three flags (REG-17, MTA-11, CA-74) + counter-notice.
5. Document Analyzer → upload `data/sample_employment_termination.txt` → parties, 15 Sep 2026 termination date, 3-day release deadline, no-notice-pay and dues-withholding clauses flagged.
6. Cases → new case is in the queue, assigned, with eligibility verdict; one seeded case shows "limitation in 9 days".
7. Admin (`?page=admin`, hidden from the sidebar) → 13 cases, per-module chart, overnight triage, deadline sentinel.

## Deploy (Mac + Cloudflare tunnel)

```bash
sh deploy/install.sh   # launchd: streamlit on 127.0.0.1:8501 + cloudflared tunnel "nyaya"
```

Tunnel config lives in `~/.cloudflared/nyaya.yml`. Logs in `logs/`.
Stop: `launchctl bootout gui/$(id -u)/com.nyaya.app` (and `.tunnel`).

## Known gaps

- Verifier correctly fails the builder demo case after one redraft (claims unsupported by facts). Add facts to the input to pass.
- Voice intake shows a transcript only; typed input stays primary.
- Hindi PDF rendering has glyph composition issues (uharfbuzz).
- Multi-clinic tenancy (Stage 5E) not built.
