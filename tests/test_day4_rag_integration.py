import json
from pathlib import Path
from unittest.mock import patch

from app.agents.coder import _rag_context, coder
from app.agents.planner import planner
from app.graph import run_task
from app.rag.embed import FakeEmbedder
from app.rag.ingest import index_repo

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "evaluation" / "bench_repo"


def test_planner_with_rag_enabled(tmp_path, monkeypatch):
    embedder = FakeEmbedder()
    p = tmp_path / "calc.py"
    p.write_text("def add_numbers(a, b):\n    return a + b\n", encoding="utf-8")
    index_repo(tmp_path, tmp_path / "chroma", embedder)

    from app.rag import retrieve

    monkeypatch.setattr(
        retrieve,
        "hybrid",
        lambda query, k, repo_path: [
            {
                "id": "calc.py::add_numbers",
                "file": "calc.py",
                "symbol": "add_numbers",
                "kind": "function",
                "start_line": 1,
                "end_line": 2,
                "code": "def add_numbers(a, b): return a + b",
                "token_estimate": 10,
            }
        ],
    )

    state = {
        "task": "add two numbers",
        "repo_path": str(tmp_path),
        "run_id": "test_run",
        "rag_enabled": True,
        "rag_mode": "hybrid",
    }

    with patch("app.agents.planner.ask_json") as mock_ask:
        mock_ask.return_value = (
            {"files": ["calc.py"], "steps": ["fix add_numbers"]},
            {"tokens": 50, "cost": 0.001, "seconds": 0.1},
        )
        res = planner(state)

    assert "retrieved_chunks" in res
    assert len(res["retrieved_chunks"]) == 1
    assert res["retrieved_chunks"][0]["symbol"] == "add_numbers"
    # Check that ask_json prompt included RAG symbols
    user_prompt = mock_ask.call_args[0][1]
    assert "RELEVANT REPO SYMBOLS (RAG):" in user_prompt
    assert "add_numbers" in user_prompt


def test_coder_context_with_rag_enabled():
    state = {
        "rag_enabled": True,
        "retrieved_chunks": [
            {
                "id": "geometry.py::Rectangle.area",
                "file": "geometry.py",
                "start_line": 10,
                "end_line": 15,
                "code": "def area(self): return self.w * self.h",
                "token_estimate": 15,
            }
        ],
    }
    ctx = _rag_context(state)
    assert "=== RETRIEVED RELEVANT CODE (RAG) ===" in ctx
    assert "[geometry.py::Rectangle.area]" in ctx
    assert "def area" in ctx


def test_coder_context_without_rag():
    state = {
        "rag_enabled": False,
        "retrieved_chunks": [{"id": "foo", "code": "bar"}],
    }
    assert _rag_context(state) == ""


def test_run_task_with_rag_end_to_end(tmp_path, monkeypatch):
    p = tmp_path / "hello.py"
    p.write_text("def hello(): return 'world'\n", encoding="utf-8")
    test_p = tmp_path / "test_hello.py"
    test_p.write_text("from hello import hello\ndef test_hello(): assert hello() == 'world'\n", encoding="utf-8")

    from app import llm

    replies = iter([
        {"files": ["hello.py"], "steps": ["return world"]},
        {"edits": {"hello.py": "def hello(): return 'world'\n"}},
        {"approved": True, "summary": "Passed", "feedback": "All good", "suggested_fixes": []},
    ])
    monkeypatch.setattr(llm, "_complete", lambda s, u: (json.dumps(next(replies)), {"tokens": 50, "cost": 0.0001, "seconds": 0.1}))

    res = run_task("make hello return world", str(tmp_path), rag=True, rag_mode="hybrid")
    assert res["status"] == "success"
    assert res["rag_enabled"] is True
