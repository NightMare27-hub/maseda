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
    from app.rag import retrieve

    # Ensure 100% offline execution without remote SSL/ONNX downloads
    monkeypatch.setattr(
        retrieve,
        "hybrid",
        lambda query, k, repo_path: [
            {
                "id": "hello.py::hello",
                "file": "hello.py",
                "symbol": "hello",
                "kind": "function",
                "start_line": 1,
                "end_line": 1,
                "code": "def hello(): return 'world'",
                "token_estimate": 10,
            }
        ],
    )

    replies = iter([
        {"files": ["hello.py"], "steps": ["return world"]},
        {"edits": {"hello.py": "def hello(): return 'world'\n"}},
        {"approved": True, "summary": "Passed", "feedback": "All good", "suggested_fixes": []},
    ])
    monkeypatch.setattr(llm, "_complete", lambda s, u: (json.dumps(next(replies)), {"tokens": 50, "cost": 0.0001, "seconds": 0.1}))

    res = run_task("make hello return world", str(tmp_path), rag=True, rag_mode="hybrid")
    assert res["status"] == "success"
    assert res["rag_enabled"] is True


def test_planner_auto_bootstraps_test_file_when_repo_has_no_tests(tmp_path):
    # Empty repo with no test files
    state = {
        "task": "build snake game engine",
        "repo_path": str(tmp_path),
        "run_id": "test_empty_repo",
    }
    with patch("app.agents.planner.ask_json") as mock_ask:
        mock_ask.return_value = (
            {"files": ["snake.py", "test_snake.py"], "steps": ["create snake.py", "write test_snake.py"]},
            {"tokens": 40, "cost": 0.0001, "seconds": 0.05},
        )
        res = planner(state)

    user_prompt = mock_ask.call_args[0][1]
    assert "NOTE: This repository currently has NO test files!" in user_prompt
    assert "test_snake.py" in res["plan"]["files"]


def test_reviewer_diagnoses_exit_code_5_and_module_not_found(tmp_path):
    from app.agents.reviewer import reviewer

    state = {
        "task": "build weather tool",
        "plan": {"files": ["weather.py"]},
        "edits": {"weather.py": "import requests"},
        "repo_path": str(tmp_path),
        "run_id": "test_rev",
        "tests_passed": False,
        "test_output": "ModuleNotFoundError: No module named 'requests'\nNo tests were collected or run (exit code 5).",
    }
    with patch("app.agents.reviewer.ask_json") as mock_ask:
        mock_ask.return_value = (
            {
                "approved": False,
                "summary": "Missing requests and tests",
                "feedback": "Use urllib instead and add pytest functions",
                "suggested_fixes": ["use urllib.request", "create test_weather.py"],
            },
            {"tokens": 60, "cost": 0.0002, "seconds": 0.1},
        )
        res = reviewer(state)

    assert res["review_approved"] is False
    system_prompt = mock_ask.call_args[0][0]
    assert "ModuleNotFoundError" in system_prompt
    assert "exit code 5" in system_prompt


def test_coder_context_large_file_outline(tmp_path):
    from app.agents.coder import _context

    p = tmp_path / "big_module.py"
    funcs = "\n\n".join(f"def func_{i}():\n    return {i}" for i in range(600))
    p.write_text(funcs, encoding="utf-8")
    state = {
        "repo_path": str(tmp_path),
        "plan": {"files": ["big_module.py"]},
    }
    ctx = _context(state)
    assert "[FILE OUTLINE" in ctx
    assert "def func_0(...)" in ctx
    assert "[FILE PREVIEW" in ctx


def test_sandbox_diagnostic_hints(tmp_path, monkeypatch):
    import subprocess
    from app.tools import sandbox

    class MockCompletedProcess:
        def __init__(self, returncode, stdout, stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    # Test EOFError hint
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: MockCompletedProcess(1, "EOFError: EOF when reading a line"))
    passed, out = sandbox.run_pytest(str(tmp_path))
    assert passed is False
    assert "[INTERACTIVE INPUT BLOCKED]" in out

    # Test Network hint
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: MockCompletedProcess(1, "urllib.error.URLError: <urlopen error [Errno -3] Temporary failure in name resolution>"))
    passed, out = sandbox.run_pytest(str(tmp_path))
    assert passed is False
    assert "[OFFLINE SANDBOX]" in out

    # Test Headless display hint
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: MockCompletedProcess(1, "pygame.error: No available video device"))
    passed, out = sandbox.run_pytest(str(tmp_path))
    assert passed is False
    assert "[HEADLESS DISPLAY]" in out

    # Test TimeoutExpired
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=30)

    monkeypatch.setattr(subprocess, "run", raise_timeout)
    passed, out = sandbox.run_pytest(str(tmp_path), timeout=30)
    assert passed is False
    assert "[SANDBOX TIME LIMIT EXCEEDED]" in out


def test_reviewer_generates_user_explanation(tmp_path):
    from app.agents.reviewer import reviewer

    state = {
        "task": "build snake game with pygame",
        "plan": {"files": ["snake.py"]},
        "edits": {"snake.py": "import pygame"},
        "repo_path": str(tmp_path),
        "run_id": "test_user_exp",
        "tests_passed": False,
        "test_output": "[HEADLESS DISPLAY]: The code attempted to open a graphical window",
    }
    with patch("app.agents.reviewer.ask_json") as mock_ask:
        mock_ask.return_value = (
            {
                "approved": False,
                "summary": "Display unavailable",
                "feedback": "Do not open Pygame windows in headless tests",
                "suggested_fixes": ["write pure snake game engine"],
                "user_explanation": "MASEDA cannot open visual game windows because our testing servers run without a computer screen. Please request a non-visual game engine.",
            },
            {"tokens": 80, "cost": 0.0003, "seconds": 0.1},
        )
        res = reviewer(state)

    assert "user_explanation" in res
    assert "cannot open visual game windows" in res["user_explanation"]
    assert res["reviewer_feedback"]["user_explanation"] == res["user_explanation"]


def test_gemini_model_cascade_generation(monkeypatch):
    from app.llm import get_model_cascade

    # Non-gemini model should return only itself
    assert get_model_cascade("openai/gpt-4o") == ["openai/gpt-4o"]

    # Mock discovered models
    monkeypatch.setattr(
        "app.llm.discover_gemini_models",
        lambda: ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-pro", "gemini-2.5-flash-lite"],
    )

    cascade = get_model_cascade("gemini/gemini-2.5-flash")
    assert cascade[0] == "gemini/gemini-2.5-flash"
    assert len(cascade) > 1
    assert any("flash" in m for m in cascade[1:])


def test_planner_prompt_includes_approach_requirement(tmp_path):
    from app.agents.planner import planner

    state = {
        "task": "build snake engine",
        "repo_path": str(tmp_path),
        "run_id": "test_approach",
    }
    with patch("app.agents.planner.ask_json") as mock_ask:
        mock_ask.return_value = (
            {
                "approach": "Building a headless SnakeGame engine with CLI",
                "logic_contract": "SnakeGame step, collision, eating logic",
                "operational_contract": "Playable terminal game loop",
                "files": ["snake.py", "test_snake.py"],
                "steps": ["step 1"],
            },
            {"tokens": 40, "cost": 0.0001, "seconds": 0.05},
        )
        res = planner(state)

    system_prompt = mock_ask.call_args[0][0]
    assert "logic_contract" in system_prompt
    assert "operational_contract" in system_prompt
    assert res["plan"]["approach"] == "Building a headless SnakeGame engine with CLI"
    assert res["plan"]["logic_contract"] == "SnakeGame step, collision, eating logic"
    assert res["plan"]["operational_contract"] == "Playable terminal game loop"


def test_reviewer_dual_gate_rejects_dummy_stubs(tmp_path):
    from app.agents.reviewer import reviewer

    state = {
        "task": "create interactive snake game",
        "plan": {"files": ["snake.py", "test_snake.py"]},
        "edits": {"snake.py": "print('static snapshot')"},
        "repo_path": str(tmp_path),
        "run_id": "test_gate2",
        "tests_passed": True,  # Gate 1 passed
        "test_output": "1 passed in 0.01s",
    }
    with patch("app.agents.reviewer.ask_json") as mock_ask:
        mock_ask.return_value = (
            {
                "approved": False,  # Gate 2 rejected due to dummy stub
                "summary": "Gate 2 failed: entrypoint is a dummy static print",
                "feedback": "Provide a real interactive while loop for human play",
                "suggested_fixes": ["implement playable while loop in main"],
                "user_explanation": "Tests passed, but the game is not playable for humans. Coder must provide an interactive loop.",
            },
            {"tokens": 50, "cost": 0.0001, "seconds": 0.05},
        )
        res = reviewer(state)

    assert res["review_approved"] is False
    system_prompt = mock_ask.call_args[0][0]
    assert "Gate 2" in system_prompt
    assert "DUAL-GATE REVIEW PROTOCOL" in system_prompt






