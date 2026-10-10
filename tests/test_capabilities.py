"""Unit tests for Surgical Patching and Multi-File Project Scaffolding."""
import json
from unittest.mock import patch

import pytest

from app.tools.patching import apply_surgical_patches, resolve_file_content
from app.tools.scaffolder import (
    extract_file_interfaces,
    get_file_tier,
    sort_files_by_dependency,
    synthesize_project_files,
)


def test_surgical_patch_exact_match():
    original = (
        "class Calculator:\n"
        "    def add(self, a, b):\n"
        "        return a + b\n\n"
        "    def multiply(self, a, b):\n"
        "        return a * b\n"
    )
    patches = [
        {
            "search": "    def add(self, a, b):\n        return a + b",
            "replace": "    def add(self, a, b):\n        # type checked add\n        return int(a) + int(b)",
        }
    ]
    updated, success, msg = apply_surgical_patches(original, patches)
    assert success is True
    assert "# type checked add" in updated
    assert "def multiply(self, a, b):" in updated  # Unmodified code preserved exactly


def test_surgical_patch_whitespace_tolerance():
    original = (
        "def compute_tax(subtotal):\n"
        "    rate = 0.05  \n"  # Trailing whitespace
        "    return subtotal * rate\n"
    )
    # Search block without trailing whitespace
    patches = [
        {
            "search": "def compute_tax(subtotal):\n    rate = 0.05\n    return subtotal * rate",
            "replace": "def compute_tax(subtotal):\n    rate = 0.08\n    return subtotal * rate",
        }
    ]
    updated, success, msg = apply_surgical_patches(original, patches)
    assert success is True
    assert "rate = 0.08" in updated


def test_surgical_patch_block_not_found():
    original = "def foo():\n    return 42\n"
    patches = [{"search": "def non_existent():\n    pass", "replace": "def replacement(): pass"}]
    updated, success, msg = apply_surgical_patches(original, patches)
    assert success is False
    assert "search block not found" in msg
    assert updated == original  # Original code preserved


def test_resolve_file_content_full_and_patch_modes():
    old = "x = 10\ny = 20\n"

    # Full mode
    res_full, ok_full, _ = resolve_file_content(old, "x = 99\ny = 20\n")
    assert ok_full is True
    assert res_full == "x = 99\ny = 20\n"

    # Patch mode
    patch_spec = {"mode": "patch", "patches": [{"search": "x = 10", "replace": "x = 50"}]}
    res_patch, ok_patch, _ = resolve_file_content(old, patch_spec)
    assert ok_patch is True
    assert res_patch == "x = 50\ny = 20\n"


def test_file_tier_and_topological_sort():
    files = [
        "tests/test_store.py",
        "app/controllers/cli.py",
        "app/models/product.py",
        "app/services/checkout.py",
        "app/config/settings.py",
    ]
    sorted_files = sort_files_by_dependency(files)

    # settings (Tier 1) -> product (Tier 2) -> checkout (Tier 4) -> cli (Tier 5) -> test_store (Tier 6)
    assert sorted_files[0] == "app/config/settings.py"
    assert sorted_files[1] == "app/models/product.py"
    assert sorted_files[2] == "app/services/checkout.py"
    assert sorted_files[3] == "app/controllers/cli.py"
    assert sorted_files[4] == "tests/test_store.py"


def test_extract_file_interfaces():
    code = (
        "class InventoryManager:\n"
        "    def __init__(self, capacity: int) -> None:\n"
        "        self.capacity = capacity\n\n"
        "    def add_stock(self, item_id: str, count: int) -> bool:\n"
        "        return True\n\n"
        "def format_currency(amount: float) -> str:\n"
        "    return f'${amount:.2f}'\n"
    )
    interfaces = extract_file_interfaces(code, "inventory.py")
    assert "class InventoryManager:" in interfaces
    assert "def add_stock(self, item_id, count): ..." in interfaces
    assert "def format_currency(amount): ..." in interfaces


def test_coder_resolves_surgical_patch_in_state(tmp_path):
    from app.agents.coder import coder

    p = tmp_path / "service.py"
    p.write_text("def run():\n    return 'v1'\n", encoding="utf-8")

    state = {
        "task": "upgrade service to v2",
        "plan": {"files": ["service.py"], "steps": ["upgrade version"]},
        "repo_path": str(tmp_path),
        "run_id": "test_patch_run",
        "iteration": 0,
        "edits": {},
    }

    mock_llm_response = {
        "edits": {
            "service.py": {
                "mode": "patch",
                "patches": [{"search": "return 'v1'", "replace": "return 'v2'"}],
            }
        }
    }

    with patch("app.agents.coder.ask_json") as mock_ask:
        mock_ask.return_value = (mock_llm_response, {"tokens": 40, "cost": 0.0001, "seconds": 0.05})
        res = coder(state)

    assert "service.py" in res["edits"]
    assert "return 'v2'" in res["edits"]["service.py"]
    assert res["edits"]["service.py"] == "def run():\n    return 'v2'\n"


def test_scaffolder_synthesizes_project_files_mock(tmp_path, monkeypatch):
    from app import llm

    files_to_build = ["models/user.py", "services/auth.py", "tests/test_auth.py"]

    responses = iter([
        # Response for models/user.py
        {"edits": {"models/user.py": "class User:\n    def __init__(self, name: str): self.name = name\n"}},
        # Response for services/auth.py
        {"edits": {"services/auth.py": "from models.user import User\ndef login(name: str): return User(name)\n"}},
        # Response for tests/test_auth.py
        {"edits": {"tests/test_auth.py": "from services.auth import login\ndef test_login(): assert login('alice').name == 'alice'\n"}},
    ])

    monkeypatch.setattr(
        llm,
        "_complete",
        lambda s, u: (json.dumps(next(responses)), {"tokens": 80, "cost": 0.0002, "seconds": 0.05}),
    )

    edits, meta = synthesize_project_files(
        task="create auth system with user model, login service, and tests",
        target_files=files_to_build,
        repo_path=str(tmp_path),
        run_id="test_scaffold_run",
    )

    assert len(edits) == 3
    assert "models/user.py" in edits
    assert "services/auth.py" in edits
    assert "tests/test_auth.py" in edits
    assert "class User:" in edits["models/user.py"]
    assert "from models.user import User" in edits["services/auth.py"]
    assert meta["tokens"] > 0


def test_reviewer_gate2_ui_ux_audit(tmp_path):
    from app.agents.reviewer import reviewer

    state = {
        "task": "build an interactive calculator",
        "plan": {"files": ["calc.py", "test_calc.py"]},
        "edits": {
            "calc.py": (
                "def main():\n"
                "    op = input('Select: 1. Add, 2. Sub: ')\n"
                "    a = float(input('Num 1: '))\n"
                "    b = float(input('Num 2: '))\n"
                "    print(a + b)\n"
            )
        },
        "repo_path": str(tmp_path),
        "run_id": "test_ui_audit",
        "tests_passed": True,  # Gate 1 passes
        "test_output": "1 passed in 0.01s",
    }

    with patch("app.agents.reviewer.ask_json") as mock_ask:
        mock_ask.return_value = (
            {
                "approved": False,
                "summary": "Gate 2 UI/UX failure: clunky single-shot interaction",
                "feedback": "Calculator uses a clunky numeric menu and terminates after one operation. Provide a continuous REPL with natural expression parsing.",
                "suggested_fixes": ["implement continuous REPL loop", "support natural expressions like 2 + 3 * 4"],
                "user_explanation": "The calculator only does one calculation and quits. It needs to stay open in a continuous loop.",
            },
            {"tokens": 50, "cost": 0.0001, "seconds": 0.05},
        )
        res = reviewer(state)

    assert res["review_approved"] is False
    system_prompt = mock_ask.call_args[0][0]
    assert "Section 5 UI/UX standards" in system_prompt
    assert "clunky, primitive input interactions" in system_prompt


def test_schema_validation_plan_and_reviewer():
    from app.schemas import PlanSchema, ReviewerSchema, validate_schema

    # Valid plan
    plan_data = {
        "approach": "Build REPL",
        "logic_contract": "evaluate()",
        "operational_contract": "calc> REPL",
        "files": ["calc.py"],
        "steps": ["step 1"],
    }
    validated_plan, err = validate_schema(plan_data, PlanSchema)
    assert err is None
    assert validated_plan["approach"] == "Build REPL"

    # Reviewer with missing optional fields gets defaults
    rev_data = {"approved": True}
    validated_rev, err = validate_schema(rev_data, ReviewerSchema)
    assert err is None
    assert validated_rev["approved"] is True
    assert validated_rev["suggested_fixes"] == []


def test_reflective_self_correction_in_ask_json(monkeypatch):
    from app import llm

    # Simulate attempt 1 returning broken text, and attempt 2 returning valid self-corrected JSON
    attempt = 0

    def mock_complete(system, user, json_mode=False):
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            return "This is not valid json at all", {"tokens": 20, "cost": 0.0001, "seconds": 0.05}
        else:
            assert "CRITICAL: Your previous response could not be validated" in user
            return '{"status": "self_corrected"}', {"tokens": 30, "cost": 0.0001, "seconds": 0.05}

    monkeypatch.setattr(llm, "_complete", mock_complete)

    data, meta = llm.ask_json("system", "give me json")
    assert data["status"] == "self_corrected"
    assert meta["attempts"] == 2


def test_workflow_error_boundary_graceful_recovery(tmp_path, monkeypatch):
    from app import graph

    p = tmp_path / "mod.py"
    p.write_text("def x(): pass\n", encoding="utf-8")

    # Force an unhandled exception inside the graph stream
    def mock_build_graph():
        class MockGraph:
            def stream(self, state):
                raise RuntimeError("Simulated unexpected graph failure")
        return MockGraph()

    monkeypatch.setattr(graph, "build_graph", mock_build_graph)

    # run_task should catch the exception gracefully without crashing
    res = graph.run_task("test task", str(tmp_path), verbose=False)
    assert res["status"] == "failed"
    assert "Simulated unexpected graph failure" in res["error"]
    assert "MASEDA encountered a workflow execution issue" in res["user_explanation"]


def test_guidelines_contain_dual_modern_ui_standards():
    from app.tools.files import load_guidelines

    guidelines = load_guidelines()
    assert "Native Desktop GUI Standard (`tkinter.ttk`)" in guidelines
    assert "Modern Web Application Standard (`streamlit`)" in guidelines
    assert "Zero extra pip installs" in guidelines
    assert "Operational Contract Selection Matrix" in guidelines


def test_planner_incorporates_dual_modern_ui_operational_contract():
    from app.agents.planner import SYSTEM

    assert "Native Desktop GUI (`tkinter.ttk`)" in SYSTEM
    assert "Modern Web UI (`streamlit`)" in SYSTEM
    assert "Continuous Terminal REPL" in SYSTEM


def test_reviewer_gate2_audits_tkinter_desktop_gui(tmp_path):
    from app.agents.reviewer import reviewer

    state = {
        "run_id": "test_run_tk",
        "task": "Create a modern desktop calculator with tkinter",
        "repo_path": str(tmp_path),
        "plan": {
            "files": ["calculator_app.py", "test_calculator.py"],
            "operational_contract": "Modern Tkinter Desktop GUI with themed ttk buttons and keyboard shortcuts",
        },
        "edits": {
            "calculator_app.py": (
                "import tkinter as tk\n"
                "from tkinter import ttk\n\n"
                "class CalculatorEngine:\n"
                "    def evaluate(self, expr):\n"
                "        return eval(expr)\n\n"
                "class CalculatorGUI:\n"
                "    def __init__(self, root):\n"
                "        self.engine = CalculatorEngine()\n"
                "        self.root = root\n\n"
                "if __name__ == '__main__':\n"
                "    root = tk.Tk()\n"
                "    app = CalculatorGUI(root)\n"
                "    root.mainloop()\n"
            )
        },
        "tests_passed": True,
        "test_output": "test_calculator.py::test_eval PASSED",
        "iteration": 1,
    }

    with patch("app.agents.reviewer.ask_json") as mock_ask:
        mock_ask.return_value = (
            {
                "approved": True,
                "summary": "Gate 1 & Gate 2 passed: Tkinter GUI implemented with clean decoupled logic",
                "feedback": "Tkinter GUI adheres to Dual-Contract with mainloop guarded.",
                "suggested_fixes": [],
                "user_explanation": "Modern Tkinter desktop calculator built. Run with: python calculator_app.py",
            },
            {"tokens": 60, "cost": 0.0001, "seconds": 0.05},
        )
        res = reviewer(state)

    assert res["review_approved"] is True
    assert "python calculator_app.py" in res["user_explanation"]
    system_prompt = mock_ask.call_args[0][0]
    assert "Native Desktop GUI deliverables (`tkinter.ttk`)" in system_prompt


def test_reviewer_gate2_audits_streamlit_web_ui(tmp_path):
    from app.agents.reviewer import reviewer

    state = {
        "run_id": "test_run_st",
        "task": "Build an interactive web calculator in streamlit",
        "repo_path": str(tmp_path),
        "plan": {
            "files": ["web_calculator.py", "test_calculator.py"],
            "operational_contract": "Modern Streamlit Web App with columns and session state",
        },
        "edits": {
            "web_calculator.py": (
                "import streamlit as st\n\n"
                "def evaluate_expression(expr):\n"
                "    return eval(expr)\n\n"
                "st.set_page_config(page_title='Modern Calculator', layout='centered')\n"
                "expr = st.text_input('Expression')\n"
                "if st.button('Calculate'):\n"
                "    st.metric('Result', evaluate_expression(expr))\n"
            )
        },
        "tests_passed": True,
        "test_output": "test_calculator.py::test_eval PASSED",
        "iteration": 1,
    }

    with patch("app.agents.reviewer.ask_json") as mock_ask:
        mock_ask.return_value = (
            {
                "approved": True,
                "summary": "Gate 1 & Gate 2 passed: Streamlit web app with metric cards and decoupled logic",
                "feedback": "Streamlit app adheres to Dual-Contract.",
                "suggested_fixes": [],
                "user_explanation": "Modern Streamlit web calculator built. Run with: streamlit run web_calculator.py",
            },
            {"tokens": 60, "cost": 0.0001, "seconds": 0.05},
        )
        res = reviewer(state)

    assert res["review_approved"] is True
    assert "streamlit run web_calculator.py" in res["user_explanation"]
    system_prompt = mock_ask.call_args[0][0]
    assert "Modern Web UI deliverables (`streamlit`)" in system_prompt


def test_dual_contract_headless_execution():
    """Verify that pure backend logic can be tested programmatically without launching GUI or Web servers."""
    class PureEngine:
        def calculate(self, a: float, b: float, op: str) -> float:
            if op == "+":
                return a + b
            elif op == "-":
                return a - b
            elif op == "*":
                return a * b
            elif op == "/":
                if b == 0:
                    raise ZeroDivisionError("Cannot divide by zero")
                return a / b
            raise ValueError(f"Unknown operator: {op}")

    engine = PureEngine()
    # Programmatic headless tests run instantly with zero GUI/browser overhead
    assert engine.calculate(10, 5, "+") == 15
    assert engine.calculate(10, 5, "-") == 5
    assert engine.calculate(10, 5, "*") == 50
    assert engine.calculate(10, 5, "/") == 2.0
    with pytest.raises(ZeroDivisionError):
        engine.calculate(10, 0, "/")



