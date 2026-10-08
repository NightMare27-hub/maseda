import os
from typing import TypedDict

MAX_ITERS = int(os.getenv("MAX_ITERS", "3"))


class State(TypedDict, total=False):
    task: str
    repo_path: str
    run_id: str
    plan: dict          # {"files": [...], "steps": [...]}
    edits: dict         # {"relative/path.py": "full new file content"}
    diff: str
    test_output: str
    tests_passed: bool
    review_approved: bool
    reviewer_feedback: dict  # {"approved": bool, "summary": str, "feedback": str, "suggested_fixes": list}
    iteration: int
    status: str         # retrying | success | failed
    stagnation_count: int
    total_tokens: int
    total_cost: float
    total_seconds: float


def route(state: State) -> str:
    """After reviewer: stop if approved, out of rounds, or stuck in repeating edits."""
    if (
        state.get("review_approved", False)
        or state.get("iteration", 0) >= MAX_ITERS
        or state.get("stagnation_count", 0) >= 2
    ):
        return "end"
    return "coder"
