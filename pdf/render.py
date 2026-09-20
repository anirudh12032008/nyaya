"""Markdown draft -> PDF bytes. Devanagari if the bundled Noto font is there, else Latin-only."""
import io
import unicodedata
from pathlib import Path

from fpdf import FPDF

FONT = Path(__file__).resolve().parent / "fonts" / "NotoSansDevanagari-Regular.ttf"


def _latin(text: str) -> str:
    """No Unicode font available: keep what Helvetica can print, drop the rest."""
    out = unicodedata.normalize("NFKD", text.replace("₹", "Rs."))
    return "".join(c for c in out if ord(c) < 256) or "[non-Latin text omitted]"


def draft_to_pdf(draft_md: str, meta: dict | None = None, qr_png: bytes | None = None) -> bytes:
    meta = meta or {}
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_page()

    unicode_ok = FONT.exists() and FONT.stat().st_size > 10000
    if unicode_ok:
        pdf.add_font("noto", "", str(FONT))
        family, bold = "noto", ""   # one weight only; size carries the emphasis
        try:  # correct Devanagari conjuncts, if uharfbuzz happens to be installed
            pdf.set_text_shaping(True)
        except Exception:
            pass
    else:
        family, bold = "helvetica", "B"

    def write(text: str, size: int, style: str = "", gap: float = 2):
        pdf.set_font(family, style, size)
        pdf.multi_cell(0, size * 0.55, text if unicode_ok else _latin(text))
        pdf.ln(gap)

    header = " · ".join(str(v) for v in
                        (meta.get("forum"), meta.get("fee_inr") is not None
                         and f"Fee Rs.{meta['fee_inr']}", meta.get("deadline_iso")
                         and f"Limitation {meta['deadline_iso']}") if v)
    if header:
        write(header, 9)

    for block in (draft_md or "").split("\n"):
        line = block.rstrip()
        if not line.strip():
            pdf.ln(2)
        elif line.lstrip().startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            write(line.lstrip("# ").strip(), 16 - min(level, 3) * 2, bold, gap=1)
        elif line.lstrip()[:2] in ("- ", "* "):
            write("  • " + line.lstrip()[2:] if unicode_ok else "  - " + line.lstrip()[2:], 11)
        else:
            write(line, 11, gap=1)

    write("Draft prepared by Nyaya for a supervising advocate's review. Not legal advice.", 8)

    if qr_png:
        pdf.image(io.BytesIO(qr_png), x=165, y=252, w=30, h=30)

    return bytes(pdf.output())


if __name__ == "__main__":
    out = draft_to_pdf("# Consumer Complaint\n\n## Facts\n- Phone worth Rs.40000\n\nमेरा फोन खराब है।",
                       {"forum": "District Commission", "fee_inr": 0, "deadline_iso": "2028-01-01"})
    assert out[:4] == b"%PDF" and len(out) > 1000, "pdf did not render"
    print(f"ok, {len(out)} bytes, unicode={FONT.exists()}")
