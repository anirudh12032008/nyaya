"""Document analyzer: empty input, happy path, bad shape, model failure — no API key needed."""
from agent import client, document_analyzer


def test_blank_document_does_not_call_the_model(monkeypatch):
    monkeypatch.setattr(client, "ask", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert "error" in document_analyzer.analyze_document("   ")


def test_happy_path_returns_the_parsed_json(monkeypatch):
    monkeypatch.setattr(client, "ask", lambda *a, **k: {"document_type": "FIR", "parties": []})
    out = document_analyzer.analyze_document("some legal text")
    assert out["document_type"] == "FIR" and "error" not in out


def test_truncates_oversized_documents(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "ask", lambda m, s, u, **k: seen.setdefault("user", u) and {} or {})
    document_analyzer.analyze_document("x" * 50000)
    assert seen["user"].count("x") == 30000


def test_non_dict_and_raising_model_both_report_an_error(monkeypatch):
    monkeypatch.setattr(client, "ask", lambda *a, **k: "not a dict")
    assert "error" in document_analyzer.analyze_document("text")
    monkeypatch.setattr(client, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert "boom" in document_analyzer.analyze_document("text")["error"]
