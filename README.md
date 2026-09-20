# Nyaya — legal aid clinic agent (Madhya Pradesh)

Intake → classify → eligibility → draft → clinic queue. Streamlit + Anthropic API + SQLite. No other external services.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
.venv/bin/python -m agent.client --selftest     # one Haiku call, prints latency
.venv/bin/python warm_cache.py                  # pre-cache every demo input (run before demo)
.venv/bin/streamlit run app.py
```

Python 3.11+ (built and tested on 3.12). Every Claude call: 45 s timeout, one retry, then served from `cache/` (SHA-256 of model+system+user). A grey **cached** tag appears in the trace when a reply came from cache.

## Stages

| Stage | What it does |
|---|---|
| 0 | Skeleton: `agent/client.py` wrapper, page router, selftest |
| 1 | Consumer complaint spine: Hindi/Hinglish/English intake → forum + fee computed in Python (`agent/forum.py`) → Sonnet draft in e-Daakhil order → section-ID guard (`agent/sections.py`) → PDF |
| 2 | Police (SHO complaint, BNSS 173(4) SP letter, zero-FIR note) and tenant (clause flags, counter-notice, PDF upload) modules; module override dropdown |
| 3 | Clinic workspace: SQLite cases, NALSA s.12 eligibility, auto-assignment, Cases queue with deadline badges, feedback, Admin metrics |
| 4 | QR on PDFs, share links, "use as template", public guides, feedback → prompt hints |

## Demo script

1. Intake → paste line 1 of `demo_inputs.txt` (Hinglish phone warranty). Show trace, forum = District, fee = nil, deadline Jan 2028, PDF.
2. Paste the builder case (₹65 lakh) → routes to State Commission, fee ₹2000.
3. Paste the refused-FIR bike theft → SHO complaint + SP letter under BNSS 173(4).
4. Paste `data/sample_rent_agreement.txt` → three flags (REG-17, MTA-11, CA-74) + counter-notice.
5. Cases → new case is in the queue, assigned, with eligibility verdict; one seeded case shows "limitation in 9 days".
6. Admin → 13 cases, per-module chart.

## Layout

See `CONTRACT.md` for module contracts and data schemas.
