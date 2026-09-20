"""Stage 5D + 5F + 5G: voice intake, filing-autopilot mock, case-similarity memory.

Owned by this stage's agent only — app.py/ui/intake.py wire these in, they don't live here.
"""
from __future__ import annotations

import html
import json
import re

import streamlit as st
import streamlit.components.v1 as components

from ui import theme


# ---------------------------------------------------------------------------
# 5D. Voice intake
# ---------------------------------------------------------------------------

def render_mic() -> str | None:
    """Browser speech-to-text via webkitSpeechRecognition (hi-IN, falls back to en-IN).

    Streamlit components can't push a value back into Python without a custom
    bidirectional component (out of scope here), so this shows the transcript in
    a textarea with a Copy button — typed input in the main intake box stays the
    source of truth. Always returns None; kept as str|None for that future upgrade.
    """
    components.html(
        """
        <div style="font-family:sans-serif">
          <button id="mic-btn" style="font-size:20px;padding:6px 14px;border-radius:8px;
                  border:1px solid #999;cursor:pointer;background:#fafafa">🎤 Speak (Hindi)</button>
          <span id="mic-status" style="margin-left:8px;color:#666;font-size:13px"></span>
          <div style="margin-top:8px">
            <textarea id="mic-text" rows="3" style="width:100%;box-sizing:border-box;
                      font-size:14px;padding:6px" placeholder="Transcript appears here…" readonly></textarea>
          </div>
          <button id="mic-copy" style="margin-top:6px;font-size:13px;padding:4px 10px;
                  border-radius:6px;border:1px solid #999;cursor:pointer;background:#fafafa">Copy</button>
          <script>
            const btn = document.getElementById('mic-btn');
            const status = document.getElementById('mic-status');
            const box = document.getElementById('mic-text');
            const copyBtn = document.getElementById('mic-copy');
            const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!Rec) {
              status.textContent = 'Speech recognition not supported in this browser.';
              btn.disabled = true;
            } else {
              const rec = new Rec();
              rec.lang = 'hi-IN';
              rec.interimResults = true;
              rec.continuous = false;
              rec.onstart = () => { status.textContent = 'Listening… (Hindi)'; };
              rec.onerror = (e) => {
                if (rec.lang === 'hi-IN') {
                  status.textContent = 'Retrying in English (en-IN)…';
                  rec.lang = 'en-IN';
                  try { rec.start(); } catch (err) {}
                } else {
                  status.textContent = 'Mic error: ' + e.error;
                }
              };
              rec.onresult = (e) => {
                let text = '';
                for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
                box.value = text;
              };
              rec.onend = () => { status.textContent = 'Stopped.'; };
              btn.onclick = () => {
                rec.lang = 'hi-IN';
                box.value = '';
                try { rec.start(); } catch (err) { status.textContent = 'Could not start mic: ' + err; }
              };
              copyBtn.onclick = () => {
                box.select();
                document.execCommand('copy');
                status.textContent = 'Copied — paste into the intake box below.';
              };
            }
          </script>
        </div>
        """,
        height=190,
    )
    st.caption(
        "Voice intake is browser speech-to-text (Hindi, falls back to English). "
        "Streamlit cannot write the transcript into the text box automatically — "
        "copy it and paste into the intake box above. Typed input stays primary."
    )
    return None


# ---------------------------------------------------------------------------
# 5G. Case-similarity memory
# ---------------------------------------------------------------------------

def render_similar(result: dict) -> None:
    """Shows 'Similar past cases' with ?case=<id> links and why, from agent.similar.find_similar."""
    from agent.similar import find_similar

    cls = (result or {}).get("classification") or {}
    facts = cls.get("facts") or {}
    summary = facts.get("what_happened") or ""
    if not summary.strip():
        return

    try:
        with st.spinner("Checking similar past cases…"):
            matches = find_similar(summary, facts)
    except RuntimeError as e:
        st.caption(f":grey[Similar cases unavailable — {e}]")
        return

    if not matches:
        return

    with theme.card("Similar past cases", "मिलते-जुलते पुराने केस — what worked there"):
        for m in matches:
            st.markdown(
                f"[Case #{m['case_id']} — {m['client_name']}](?case={m['case_id']}) &nbsp;"
                + theme.badge(m["module"], "info") + " " + theme.badge(m["what_worked"], "ok"),
                unsafe_allow_html=True)
            if m.get("why"):
                st.caption(m["why"])


# ---------------------------------------------------------------------------
# 5F. Filing autopilot preview (mock e-Daakhil form)
# ---------------------------------------------------------------------------

def _relief_from_draft(draft_md: str) -> str:
    m = re.search(r"##\s*Relief Sought\s*\n(.*?)(\n##|\Z)", draft_md or "", re.S | re.I)
    return m.group(1).strip() if m else "[TO CONFIRM]"


def render_autopilot(result: dict) -> None:
    """Mock e-Daakhil form filled field-by-field by a JS typing animation. Consumer module only."""
    cls = (result or {}).get("classification") or {}
    if cls.get("module") != "consumer":
        return
    draft = (result or {}).get("draft") or {}
    facts = cls.get("facts") or {}

    parties = facts.get("parties") or []
    parties = [p if isinstance(p, str) else (p.get("name") if isinstance(p, dict) else str(p))
               for p in parties]
    parties = [p for p in parties if p]

    fields = {
        "Complainant name": parties[0] if parties else "[TO CONFIRM]",
        "Opposite party": parties[1] if len(parties) > 1 else "[TO CONFIRM]",
        "Claim amount": f"Rs. {facts.get('amount_inr')}" if facts.get("amount_inr") else "[TO CONFIRM]",
        "Cause of action date": facts.get("date_of_cause") or "[TO CONFIRM]",
        "Facts": facts.get("what_happened") or "[TO CONFIRM]",
        "Relief": _relief_from_draft(draft.get("draft_markdown", "")),
    }

    st.caption("MOCK — a demo of the e-Daakhil form filling itself. "
               "Nothing is submitted anywhere.")

    rows = "".join(
        f"""
        <div style="margin-bottom:10px">
          <label style="display:block;font-size:12px;color:#666;margin-bottom:2px">{html.escape(k)}</label>
          <textarea id="af-{i}" rows="{1 if k not in ('Facts', 'Relief') else 3}"
                    style="width:100%;box-sizing:border-box;font-size:13px;padding:6px;
                           border:1px solid #ccc;border-radius:4px" readonly></textarea>
        </div>"""
        for i, k in enumerate(fields)
    )

    components.html(
        f"""
        <div style="font-family:sans-serif;border:1px solid #ddd;border-radius:8px;padding:14px">
          <div style="font-weight:600;margin-bottom:10px">e-Daakhil — New Complaint (MOCK)</div>
          {rows}
          <button id="af-play" style="font-size:14px;padding:6px 14px;border-radius:8px;
                  border:1px solid #999;cursor:pointer;background:#fafafa">▶ Autofill</button>
          <button id="af-submit" disabled title="Live filing once portal auth is available."
                  style="font-size:14px;padding:6px 14px;border-radius:8px;margin-left:8px;
                         border:1px solid #ccc;cursor:not-allowed;background:#eee;color:#888">Submit</button>
          <div style="margin-top:6px;font-size:12px;color:#888">
            Live filing once portal auth is available.
          </div>
          <script>
            const values = {json.dumps(list(fields.values()), ensure_ascii=False)};
            const playBtn = document.getElementById('af-play');
            async function typeInto(el, text) {{
              el.value = '';
              el.style.caretColor = '#000';
              for (let i = 0; i < text.length; i++) {{
                el.value += text[i];
                await new Promise(r => setTimeout(r, 12));
              }}
            }}
            playBtn.onclick = async () => {{
              playBtn.disabled = true;
              for (let i = 0; i < values.length; i++) {{
                const el = document.getElementById('af-' + i);
                el.focus();
                await typeInto(el, values[i]);
              }}
              playBtn.disabled = false;
            }};
          </script>
        </div>
        """,
        height=430 + 46 * max(0, len(fields) - 6),
    )
