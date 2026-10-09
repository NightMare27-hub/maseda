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
                           capture_output=True, text=True, errors="replace", timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, (
            f"[SANDBOX TIME LIMIT EXCEEDED]: Execution timed out after {timeout} seconds. "
            "This usually indicates an infinite loop (e.g. while True), interactive console waiting (e.g. input()), "
            "or an extremely slow algorithm."
        )
    output = (r.stdout + r.stderr)[-4000:]

    hints = []
    if r.returncode == 5:
        hints.append("[NO TESTS FOUND]: No pytest test functions (def test_...) were discovered (exit code 5).")
    if "EOFError" in output or "stdin" in output.lower():
        hints.append("[INTERACTIVE INPUT BLOCKED]: The code attempted to read from keyboard/console input (e.g. input()), but automated sandbox tests run non-interactively without a keyboard.")
    if any(net in output for net in ("socket.gaierror", "URLError", "ConnectionRefusedError", "ConnectionError")):
        hints.append("[OFFLINE SANDBOX]: The code attempted an external internet network call, but the test environment has no network access.")
    if any(gui in output for gui in ("no display name", "TclError", "pygame.error: No available video device")):
        hints.append("[HEADLESS DISPLAY]: The code attempted to open a graphical window (GUI), but the test environment runs headlessly with no desktop screen.")

    if hints:
        output = "\n".join(hints) + "\n\n" + output
    return r.returncode == 0, output.strip()


def run_tests(repo: str, edits: dict):
    work = prepare_workdir(repo, edits)
    try:
        return run_pytest(work)
    finally:
        shutil.rmtree(os.path.dirname(work), ignore_errors=True)
