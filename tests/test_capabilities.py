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

