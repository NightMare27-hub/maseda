"""Offline tests: the LLM is faked, so no API key or network is needed."""
import json
import shutil
from pathlib import Path

import pytest

from app import llm
from app.tools.files import apply_edits, is_test_file, make_diff, safe_path

TOY = Path(__file__).resolve().parent.parent / "evaluation" / "toy_repo"

GOOD = '''def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
'''
BAD = GOOD.replace('raise ValueError("Cannot divide by zero")', "return 0")
PLAN = {"files": ["calculator.py"], "steps": ["add divide"]}


def fake_llm(monkeypatch, replies):
    it = iter(replies)
    monkeypatch.setattr(llm, "_complete", lambda s, u: (json.dumps(next(it)), {"tokens": 1, "cost": 0, "seconds": 0}))


@pytest.fixture
def repo(tmp_path):
    dest = tmp_path / "repo"
    shutil.copytree(TOY, dest, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return str(dest)


REV_OK = {"approved": True, "summary": "All tests pass and code is correct", "feedback": "Looks good", "suggested_fixes": []}
REV_FAIL = {"approved": False, "summary": "Tests failed", "feedback": "Need to raise ValueError", "suggested_fixes": ["raise ValueError"]}


def test_parse_json_handles_fences_and_noise():
    assert llm.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm.parse_json('Sure! {"a": 1} done') == {"a": 1}
    with pytest.raises(ValueError):
        llm.parse_json("no json here")


def test_safe_path_blocks_escape(repo):
    with pytest.raises(ValueError):
        safe_path(repo, "../outside.py")
    with pytest.raises(ValueError):
        safe_path(repo, "/etc/passwd")


def test_diff_and_test_file_detection(repo):
    assert "+def divide" in make_diff(repo, {"calculator.py": GOOD})
    assert is_test_file("test_calculator.py") and not is_test_file("calculator.py")


def test_first_attempt_passes(monkeypatch, repo):
    from app.graph import run_task
    fake_llm(monkeypatch, [PLAN, {"edits": {"calculator.py": GOOD}}, REV_OK])
    r = run_task("add divide", repo)
    assert r["status"] == "success" and r["iteration"] == 1
    assert r["review_approved"] is True


def test_fix_loop_recovers_from_failure(monkeypatch, repo):
    from app.graph import run_task
    fake_llm(monkeypatch, [PLAN, {"edits": {"calculator.py": BAD}}, REV_FAIL, {"edits": {"calculator.py": GOOD}}, REV_OK])
    r = run_task("add divide", repo)
    assert r["status"] == "success" and r["iteration"] == 2


def test_coder_cannot_edit_tests(monkeypatch, repo):
    from app.graph import run_task
    cheat = {"edits": {"calculator.py": GOOD, "test_calculator.py": "def test_x():\n    assert True\n"}}
    fake_llm(monkeypatch, [PLAN, cheat, REV_OK])
    r = run_task("add divide", repo)
    assert "test_calculator.py" not in r["edits"]


def test_gives_up_after_max_rounds(monkeypatch, repo):
    from app.graph import run_task
    fake_llm(monkeypatch, [
        PLAN,
        {"edits": {"calculator.py": BAD}}, REV_FAIL,
        {"edits": {"calculator.py": BAD}}, REV_FAIL,
        {"edits": {"calculator.py": BAD}}, REV_FAIL,
    ])
    r = run_task("add divide", repo)
    assert r["status"] == "failed" and r["iteration"] == 3


def test_reviewer_rejects_when_not_approved(monkeypatch, repo):
    from app.graph import run_task
    # Even if tests pass, reviewer can reject if implementation has issues
    fake_llm(monkeypatch, [
        PLAN,
        {"edits": {"calculator.py": GOOD}}, REV_FAIL,
        {"edits": {"calculator.py": GOOD}}, REV_OK,
    ])
    r = run_task("add divide", repo)
    assert r["status"] == "success" and r["iteration"] == 2


def test_parse_json_markdown_blocks_and_trailing_commas():
    # commentary + markdown code fence
    text_fence = "Here is the response:\n```json\n{\"files\": [\"math.py\"], \"steps\": [\"step 1\"]}\n```\nEnjoy!"
    assert llm.parse_json(text_fence) == {"files": ["math.py"], "steps": ["step 1"]}

    # trailing commas in JSON
    text_trailing = '{"files": ["calc.py", ], "steps": ["do this", ], }'
    assert llm.parse_json(text_trailing) == {"files": ["calc.py"], "steps": ["do this"]}


def test_run_task_tracks_metrics_and_creates_new_file(monkeypatch, repo):
    from app.graph import run_task
    new_plan = {"files": ["calculator.py", "helper.py"], "steps": ["create helper", "update calculator"]}
    new_edits = {
        "calculator.py": GOOD,
        "helper.py": "# helper module\ndef check_nonzero(val):\n    return val != 0\n",
    }
    fake_llm(monkeypatch, [new_plan, {"edits": new_edits}, REV_OK])
    r = run_task("add helper and divide", repo)
    assert r["status"] == "success"
    assert "helper.py" in r["edits"]
    assert r["total_tokens"] >= 3
    assert r["total_cost"] >= 0.0
    assert r["total_seconds"] >= 0.0


def test_sandbox_run_pytest_code_5_diagnostic(tmp_path):
    from app.tools.sandbox import run_pytest
    empty_dir = tmp_path / "empty_repo"
    empty_dir.mkdir()
    passed, output = run_pytest(str(empty_dir))
    assert not passed
    assert "exit code 5" in output
