"""Anthropic wrapper: 45s timeout, one retry, SHA-256 file cache, JSON mode.

ask(model, system, user, json_mode=False, temperature=0.0) -> str | dict
Every call is cached to cache/<sha256(model+system+user)>.json so the demo
replays if the API or wifi dies. The last call's metadata (ms, cached flag)
is available via last_trace() for the UI trace panel.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

try:  # optional: load .env from repo root so the key never has to be exported
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-6"
TIMEOUT_S = 45.0

_client = None
_last_trace: dict = {}


def _get_client():
    global _client
    if _client is None:
        import anthropic  # lazy so the app opens without the SDK installed
        _client = anthropic.Anthropic(timeout=TIMEOUT_S, max_retries=0)
    return _client


def _key(model: str, system: str, user: str) -> str:
    return hashlib.sha256((model + "\x00" + system + "\x00" + user).encode()).hexdigest()


def _strip_fences(text: str) -> str:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    # tolerate leading prose before the first brace
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=0)
    return text[start:]


def _parse_json(text: str):
    return json.loads(_strip_fences(text))


def _call_api(model: str, system: str, user: str, temperature: float, max_tokens: int) -> str:
    # Streaming keeps the socket alive on long drafts; TIMEOUT_S still bounds each read.
    with _get_client().messages.stream(
        model=model,
        max_tokens=max_tokens,  # SDK 1.x: no temperature param; kept in signature for callers
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        resp = stream.get_final_message()
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def _text_of(user) -> str:
    """The prompt as plain text; content-block lists lose their non-text parts."""
    if isinstance(user, str):
        return user
    return "\n".join(b.get("text", "") for b in user
                     if isinstance(b, dict) and b.get("type") == "text")


def last_trace() -> dict:
    return dict(_last_trace)


def ask(model: str, system: str, user, json_mode: bool = False,
        temperature: float = 0.0, max_tokens: int = 8192, use_cache: bool = True,
        cache_key: str | None = None):
    """Call Claude with timeout + one retry, falling back to the file cache.

    Returns the text reply, or a parsed dict/list when json_mode=True.
    Raises RuntimeError only if the API fails twice AND nothing is cached.
    """
    global _last_trace
    key = _key(model, system, user if cache_key is None else cache_key)
    path = CACHE_DIR / f"{key}.json"
    t0 = time.time()

    if use_cache and path.exists():
        cached = json.loads(path.read_text())
        _last_trace = {"model": model, "ms": int((time.time() - t0) * 1000), "cached": True}
        return cached["parsed"] if json_mode and "parsed" in cached else cached["text"]

    text, err = None, None
    for attempt in range(2):
        try:
            text = _call_api(model, system, user, temperature, max_tokens)
            break
        except Exception as e:  # timeout, connection, 5xx, auth
            err = e
            time.sleep(1)

    if text is None:
        if path.exists():  # both attempts failed -> serve stale cache
            cached = json.loads(path.read_text())
            _last_trace = {"model": model, "ms": int((time.time() - t0) * 1000), "cached": True}
            return cached["parsed"] if json_mode and "parsed" in cached else cached["text"]
        raise RuntimeError(f"Claude call failed twice and no cache: {err}")

    parsed = None
    if json_mode:
        try:
            parsed = _parse_json(text)
        except (json.JSONDecodeError, ValueError) as e:
            repair = (_text_of(user) + "\n\n[SYSTEM] Your previous reply was not valid JSON (" + str(e)[:120]
                      + "). Return the same content as ONLY valid JSON: escape quotes and newlines "
                      "inside strings, no prose, no code fences.\n\nPrevious reply:\n" + text[:6000])
            text = _call_api(model, system + "\n\nReturn ONLY valid JSON.", repair, temperature, max_tokens)
            parsed = _parse_json(text)  # let it raise if still broken

    record = {"model": model, "text": text, "ts": time.time()}
    if parsed is not None:
        record["parsed"] = parsed
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1))
    _last_trace = {"model": model, "ms": int((time.time() - t0) * 1000), "cached": False}
    return parsed if json_mode else text


def ask_image(model: str, system: str, prompt: str, image_bytes: bytes,
              mime: str = "image/png", json_mode: bool = False, max_tokens: int = 2048):
    """ask() for one image. Same cache + trace; the cache key covers the bytes."""
    content = [{"type": "image",
                "source": {"type": "base64", "media_type": mime,
                           "data": base64.standard_b64encode(image_bytes).decode()}},
               {"type": "text", "text": prompt}]
    return ask(model, system, content, json_mode=json_mode, max_tokens=max_tokens,
               cache_key=prompt + "\x00" + hashlib.sha256(image_bytes).hexdigest())


def selftest() -> None:
    t0 = time.time()
    reply = ask(HAIKU, "You are a terse assistant.", "Say 'Nyaya ready' in Hindi and English.",
                use_cache=False, max_tokens=64)
    print(f"[{int((time.time() - t0) * 1000)} ms] {reply}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        selftest()
    else:
        print(__doc__)
