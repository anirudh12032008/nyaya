"""Run every demo input through the pipeline so cache/ is warm before the demo."""
import os
import sys
from pathlib import Path

from agent.pipeline import run_intake

ROOT = Path(__file__).resolve().parent


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set — skipping warm-up (the app will serve cache/).")
        return 0
    for line in (ROOT / "demo_inputs.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = run_intake(line)
        if r.get("missing_fact") and not r.get("draft"):
            r = run_intake(line, answers="Not sure")
        f, d = r.get("forum") or {}, r.get("draft") or {}
        print(f"\n{line[:70]}…\n  forum={f.get('forum')} fee=Rs.{f.get('fee_inr')} "
              f"deadline={d.get('deadline_iso')} dropped={r.get('sections_dropped')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
