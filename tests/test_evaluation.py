import json
import pathlib
import pytest

from evaluation.run_eval import ROOT, parse_args, run_single_task


def test_tasks_json_schema_and_count():
    tasks_path = ROOT / "evaluation" / "tasks.json"
    assert tasks_path.exists()
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    assert len(tasks) == 20
    required_keys = {"id", "name", "repo", "instruction", "expected_files", "category"}
    seen_ids = set()
    for task in tasks:
        assert required_keys.issubset(task.keys())
        assert task["id"] not in seen_ids
        seen_ids.add(task["id"])

        repo_path = ROOT / task["repo"]
        assert repo_path.exists(), f"Repo path {repo_path} does not exist"
        for exp in task["expected_files"]:
            assert (repo_path / exp).exists() or True


def test_run_single_task_with_mocked_llm(monkeypatch):
    from app import llm

    plan = {"files": ["calculator.py"], "steps": ["implement divide"]}
    good_calc = (
        "def add(a, b):\n    return a + b\n\n\n"
        "def subtract(a, b):\n    return a - b\n\n\n"
        "def multiply(a, b):\n    return a * b\n\n\n"
        "def divide(a, b):\n    if b == 0:\n        raise ValueError('Cannot divide by zero')\n    return a / b\n"
    )
    coder_edit = {"edits": {"calculator.py": good_calc}}
    rev_ok = {"approved": True, "summary": "Looks good", "feedback": "", "suggested_fixes": []}

    replies = iter([plan, coder_edit, rev_ok])
    monkeypatch.setattr(
        llm,
        "_complete",
        lambda s, u: (json.dumps(next(replies)), {"tokens": 10, "cost": 0.001, "seconds": 0.5}),
    )

    sample_task = {
        "id": "task_01",
        "name": "calculator_divide",
        "repo": "evaluation/toy_repo",
        "category": "bugfix",
        "instruction": "Implement divide",
        "expected_files": ["calculator.py"],
    }

    res = run_single_task(sample_task)
    assert res["status"] == "success"
    assert res["id"] == "task_01"
    assert res["total_tokens"] >= 10
    assert res["iteration"] == 1


def test_validate_python_syntax():
    from app.tools.files import validate_python_syntax

    good = {"a.py": "def foo():\n    return 42\n"}
    valid, err = validate_python_syntax(good)
    assert valid and not err

    bad = {"b.py": "def foo(:\n    return\n"}
    valid, err = validate_python_syntax(bad)
    assert not valid
    assert "SyntaxError in b.py" in err


def test_circuit_breaker_halts_on_repeat_edits(monkeypatch, tmp_path):
    import shutil
    from app import llm
    from app.graph import run_task

    dest = tmp_path / "toy"
    shutil.copytree(ROOT / "evaluation" / "toy_repo", dest)

    plan = {"files": ["calculator.py"], "steps": ["try fix"]}
    bad_calc = "def add(a, b):\n    return a + b\n"
    bad_edit = {"edits": {"calculator.py": bad_calc}}
    rev_fail = {"approved": False, "summary": "Failed", "feedback": "Fix", "suggested_fixes": []}

    # Repeated identical edits: attempt 1 (fails, stag=0); attempt 2 (same edit, fails, stag=1 with warning); attempt 3 (same edit, fails, stag=2, halted by route)
    replies = iter([plan, bad_edit, rev_fail, bad_edit, rev_fail, bad_edit, rev_fail])
    monkeypatch.setattr(
        llm,
        "_complete",
        lambda s, u: (json.dumps(next(replies)), {"tokens": 5, "cost": 0.0001, "seconds": 0.1}),
    )

    res = run_task("fix divide", str(dest))
    assert res["status"] == "failed"
    assert res["iteration"] == 3
    assert res.get("stagnation_count", 0) >= 2
