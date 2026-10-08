"""Runs the test suite on a COPY of the repo with the proposed edits applied.

WARNING: this runs generated code locally in a temp folder with a minimal environment
(no API keys passed). It is NOT isolated. Day 6: replace run_pytest with a Docker run
(no network, memory and CPU limits).
"""
import os
import shutil
import subprocess
import sys
import tempfile

from app.tools.files import apply_edits

_KEEP_ENV = ("PATH", "SYSTEMROOT", "HOME", "TEMP", "TMP", "LANG")


def prepare_workdir(repo: str, edits: dict) -> str:
    parent = tempfile.mkdtemp(prefix="maseda_")
    work = os.path.join(parent, "repo")
    shutil.copytree(repo, work, ignore=shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", ".pytest_cache", "*.pyc"))
    apply_edits(work, edits)
    return work


def run_pytest(workdir: str, timeout: int = 60):
    env = {k: v for k, v in os.environ.items() if k in _KEEP_ENV}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = workdir
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q"], cwd=workdir,
                           capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, f"Timed out after {timeout}s"
    output = (r.stdout + r.stderr)[-4000:]
    if r.returncode == 5:
        output = f"No tests were collected or run (exit code 5).\n{output}".strip()
    return r.returncode == 0, output


def run_tests(repo: str, edits: dict):
    work = prepare_workdir(repo, edits)
    try:
        return run_pytest(work)
    finally:
        shutil.rmtree(os.path.dirname(work), ignore_errors=True)
