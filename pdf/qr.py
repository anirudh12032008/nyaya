"""QR codes that point a phone back at a case in this app."""
from __future__ import annotations

import io
import os
from urllib.parse import urlencode

import qrcode

DEFAULT_BASE = "http://localhost:8501"


def base_url() -> str:
    return (os.environ.get("NYAYA_BASE_URL") or DEFAULT_BASE).rstrip("/")


def make_qr_png(url: str) -> bytes:
    buf = io.BytesIO()
    qrcode.make(url).save(buf, format="PNG")
    return buf.getvalue()


def case_url(case_id: int, clinic: str = "nliu", **extra) -> str:
    return f"{base_url()}/?" + urlencode({"case": case_id, "clinic": clinic, **extra})


def qr_for_case(case_id: int, clinic: str = "nliu") -> bytes:
    """QR encoding ?case=<id>&clinic=<slug> - used on the PDF and by intake."""
    return make_qr_png(case_url(case_id, clinic))


if __name__ == "__main__":
    png = qr_for_case(7)
    assert png[:4] == b"\x89PNG", "not a png"
    print(f"ok, {len(png)} bytes, {case_url(7)}")
