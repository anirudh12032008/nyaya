"""Orchestra + chat: council fans out, tolerates one failed agent, persists; chat tools dispatch."""
import json

from agent import chat, client, orchestra
from db import db


def _fake_ask(model, system, user, json_mode=False, **kw):
    if "DEVIL'S ADVOCATE" in system:
        raise RuntimeError("boom")
    if json_mode:
        return {"role": system.split("Role: ")[1].split(".")[0], "model": model}
    return "## Verdict\nfake brief"


def test_council_parallel_and_persisted(monkeypatch):
    monkeypatch.setattr(client, "ask", _fake_ask)
    db.init()
    case = db.list_cases()[0]
    seen = []
    out = orchestra.council_for_case(case["id"], force=True,
                                     on_agent_done=lambda n, ok, ms: seen.append((n, ok)))
    assert set(out["agents"]) == set(orchestra.SPECIALISTS) - {"opponent"}
    assert out["errors"] == {"opponent": "boom"}
    assert out["brief_md"].startswith("## Verdict")
    assert ("opponent", False) in seen and ("synthesis", True) in seen
    stored = json.loads(db.get_case(case["id"])["council_json"])
    assert stored["brief_md"] == out["brief_md"]
    # second call without force reuses the stored brief, no agents run
    monkeypatch.setattr(client, "ask", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert orchestra.council_for_case(case["id"])["brief_md"] == out["brief_md"]


def test_chat_tools_dispatch(monkeypatch):
    db.init()
    rows = chat.dispatch("list_cases", {"status": None})
    assert rows and {"id", "client_name", "deadline"} <= set(rows[0])
    c = chat.dispatch("get_case", {"case_id": rows[0]["id"]})
    assert "trace_json" not in c and "days_to_deadline" in c
    assert chat.dispatch("compute_forum", {"amount_inr": 320000})["forum"]
    assert chat.dispatch("search_sections", {"module": "police", "query": "theft"})
    assert chat.dispatch("get_case", {"case_id": 999999})["error"]
