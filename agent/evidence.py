"""Evidence checklist + annexure uploads for one case.

checklist(case)             -> [{"item","why","have"}]   portals.json documents first
label_upload(...)           -> {"label","kind","summary","matches_item"}; stores the file
                               under uploads/<case_id>/ and inserts an `annexures` row
annexure_index_md(case_id)  -> "## Annexures" markdown ("Annexure A-1 …")
attach_annexure_index(id)   -> append that block to cases.draft_md, idempotently
"""
from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path

from agent import client
from agent.data import load
from db import db

ROOT = Path(__file__).resolve().parent.parent
UPLOADS = Path(os.environ.get("NYAYA_UPLOADS") or ROOT / "uploads")
MAX_ITEMS = 8
MARKER = "<!-- nyaya:annexure-index -->"
MAX_TEXT_CHARS = 6000

_CHECKLIST_SYS = """You are a legal-aid clinic filing clerk in Madhya Pradesh, India.
Given a case and the portal's standard document list, say what the client must produce to file.
Keep every standard document, then add at most a few items specific to THESE facts.
Return ONLY JSON: {"items": [{"item": str, "why": str}]}
"item" is the document's name — reuse the standard wording verbatim where it applies.
"why" is one short line on what it proves. Never invent facts about the case."""

_LABEL_SYS = """You are a legal-aid clinic clerk labelling one document a client has uploaded.
Return ONLY JSON: {"label": str, "kind": str, "summary": str, "matches_item": str}
"label": short filing label, e.g. "Invoice dated 12 Mar 2024".
"kind": one of invoice, receipt, id_proof, agreement, notice, photo, medical, correspondence, other.
"summary": one or two sentences on what the document actually shows.
"matches_item": the checklist item this document satisfies, copied VERBATIM from the candidate
list, or "" if none fits. Describe only what you can see; never invent content."""


# ---------------------------------------------------------------- checklist

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _seed_documents(module) -> list[str]:
    return list(load("portals").get(module or "", {}).get("documents") or [])


def _matched_items(case_id) -> set[str]:
    if not case_id:
        return set()
    return {k for k in (_norm(a.get("matches_item")) for a in db.list_annexures(case_id)) if k}


def checklist(case: dict) -> list[dict]:
    """Documents this filing needs. portals.json items first (deterministic), max 8."""
    seed = _seed_documents(case.get("module"))
    user = (f"MODULE: {case.get('module')}\nSUMMARY: {case.get('summary') or ''}\n"
            f"FACTS JSON:\n{case.get('facts_json') or '{}'}\n\n"
            f"STANDARD DOCUMENTS:\n{json.dumps(seed, ensure_ascii=False, indent=1)}")
    try:
        raw = client.ask(client.HAIKU, _CHECKLIST_SYS, user, json_mode=True)
    except Exception:  # no key and no cache: the portal list alone is still worth showing
        raw = {}

    whys, extras = {}, []
    for entry in (raw.get("items") if isinstance(raw, dict) else raw) or []:
        item = ((entry.get("item") if isinstance(entry, dict) else entry) or "").strip()
        if not item:
            continue
        whys.setdefault(_norm(item), (entry.get("why") if isinstance(entry, dict) else "") or "")
        extras.append(item)

    done, out, seen = _matched_items(case.get("id")), [], set()
    for item in seed + extras:  # portals.json first, whatever order the model replied in
        k = _norm(item)
        if k in seen:
            continue
        seen.add(k)
        out.append({"item": item, "why": whys.get(k) or "Standard document for this forum.",
                    "have": k in done})
        if len(out) >= MAX_ITEMS:
            break
    return out


# ---------------------------------------------------------------- uploads

def safe_name(filename: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename or "file").name)[:120] or "file"


def _pdf_text(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages)
    except Exception:
        return ""


def extract_text(raw: bytes, mime: str, filename: str = "") -> str:
    """Plain text from a PDF or text-ish upload. Empty for images/binaries."""
    if (mime or "").endswith("pdf") or filename.lower().endswith(".pdf"):
        return _pdf_text(raw)[:MAX_TEXT_CHARS]
    try:
        return raw.decode("utf-8")[:MAX_TEXT_CHARS]
    except UnicodeDecodeError:
        return ""


def label_upload(case_id: int, filename: str, raw: bytes, mime: str) -> dict:
    """Store one annexure and let Claude label it. Images go through vision."""
    case = db.get_case(case_id) or {}
    candidates = [row["item"] for row in checklist(case)] if case else []
    prompt = ("CANDIDATE CHECKLIST ITEMS:\n"
              + json.dumps(candidates, ensure_ascii=False, indent=1)
              + f"\n\nCASE SUMMARY: {case.get('summary') or ''}\nFILENAME: {filename}")

    dest = UPLOADS / str(case_id) / safe_name(filename)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)

    if (mime or "").startswith("image/"):
        out = client.ask_image(client.HAIKU, _LABEL_SYS, prompt, raw, mime=mime, json_mode=True)
    else:
        text = extract_text(raw, mime, filename)
        out = client.ask(client.HAIKU, _LABEL_SYS,
                         prompt + "\n\nDOCUMENT TEXT:\n" + (text or "[no extractable text]"),
                         json_mode=True)
    out = out if isinstance(out, dict) else {}

    by_norm = {_norm(c): c for c in candidates}
    match = by_norm.get(_norm(out.get("matches_item")), "")  # drop anything not on the list
    result = {"label": (out.get("label") or safe_name(filename)).strip(),
              "kind": (out.get("kind") or "other").strip().lower(),
              "summary": (out.get("summary") or "").strip(),
              "matches_item": match}
    db.add_annexure(case_id, safe_name(filename), str(dest), result["kind"],
                    result["label"], result["summary"], match)
    return result


# ---------------------------------------------------------------- annexure index

def annexure_index_md(case_id: int) -> str:
    rows = db.list_annexures(case_id)
    if not rows:
        return ""
    lines = ["## Annexures", ""]
    for n, a in enumerate(rows, 1):
        bits = [f"**Annexure A-{n}** — {a.get('label') or a.get('filename')}"]
        if a.get("summary"):
            bits.append(a["summary"])
        bits.append(f"(file: {a.get('filename')})")
        lines.append("- " + " · ".join(bits))
    return "\n".join(lines) + "\n"


def attach_annexure_index(case_id: int) -> bool:
    """Append the annexure index to the draft once. Re-running replaces the same block."""
    md = annexure_index_md(case_id)
    if not md:
        return False
    case = db.get_case(case_id) or {}
    draft = (case.get("draft_md") or "").split(MARKER)[0].rstrip()
    new = f"{draft}\n\n{MARKER}\n{md}"
    if new == (case.get("draft_md") or ""):
        return False
    db.update_case(case_id, draft_md=new)
    return True
