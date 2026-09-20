# Nyaya — legal aid clinic agent (Madhya Pradesh)

A citizen describes a problem in Hindi, Hinglish or English. Nyaya classifies it (consumer,
police, tenant), works out the forum, fee and deadline, drafts the filing, checks the draft with
a second model pass, renders a PDF, and drops the case into a clinic queue with an eligibility
verdict and an assigned volunteer.

Stack: Streamlit + Anthropic API + SQLite. No other services. Live at https://nyaya.workwithani.tech.

Contributing? Read [CONTRIBUTING.md](CONTRIBUTING.md) first (branch → PR → review → squash).
Module contracts and data schemas live in [CONTRACT.md](CONTRACT.md).

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
| 8 | Labour module: unpaid wages, termination, PF/ESI, gratuity. Forum + limitation from `data/labour_rules.json` in Python; PWA s.15 claim + demand letter (Sonnet) | `agent/labour.py` |
| 9 | Evidence: Haiku checklist per module, upload photos/PDFs, Haiku vision labels each one, annexure index appended to the draft | `agent/evidence.py`, `ui/evidence.py` |
| 10 | Outcomes + volunteer copilot: record won/lost/settled, similar cases and `## Learned` use real outcomes; Opus plans call script + 3 dated next actions | `agent/copilot.py`, `ui/copilot.py` |
| 11 | Audit trail: per-case timeline, model calls, verifier verdict, council run, Haiku plain summary, PDF export for funders/DLSA. Also an Ask Nyaya tool | `agent/audit.py`, `ui/audit.py` |
| 7 | Ask Nyaya: agentic chatbot (Opus 5 tool-use loop) over the workspace — lists/opens cases, searches statutes, computes forum + fee, finds similar cases, runs the council, updates status | `agent/chat.py`, `ui/chat.py` (floating 💬 bubble, bottom-right of every page) |

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
5. Cases → new case is in the queue, assigned, with eligibility verdict; one seeded case shows "limitation in 9 days".
6. Admin (`?page=admin`, hidden from the sidebar) → 13 cases, per-module chart, overnight triage, deadline sentinel.

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
