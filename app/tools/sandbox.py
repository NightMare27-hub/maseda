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

_KEEP_ENV = ("PATH", "SYSTEMROOT", "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "TEMP", "TMP", "LANG")


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
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--maxfail=10"], cwd=workdir,
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


def run_entrypoint_smoke_tests(workdir: str, timeout: int = 15) -> tuple[bool, str]:
    """Execute headless smoke tests on non-test entrypoints and UI scripts.

    Detects top-level attribute errors, broken imports, and UI runtime crashes
    that automated pytest units miss because pytest only executes test files.
    """
    import pathlib
    from app.tools.files import is_test_file, list_py_files

    env = {k: v for k, v in os.environ.items() if k in _KEEP_ENV}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = workdir

    py_files = list_py_files(workdir)
    entrypoints = [f for f in py_files if not is_test_file(f)]

    for rel in entrypoints:
        full_path = os.path.abspath(os.path.join(workdir, rel))
        try:
            content = pathlib.Path(full_path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # 1. Streamlit Headless Smoke Test via official AppTest
        if "import streamlit" in content or "from streamlit" in content:
            # Escape path backslashes for Windows
            clean_path = full_path.replace("\\", "\\\\")
            runner_script = (
                "import sys\n"
                "from streamlit.testing.v1 import AppTest\n"
                "try:\n"
                f"    at = AppTest.from_file(r'{clean_path}').run(timeout=10)\n"
                "    if at.exception:\n"
                "        err = at.exception[0]\n"
                "        stack = '\\n'.join(getattr(err, 'stack_trace', []))\n"
                "        msg = getattr(err, 'value', '') or getattr(err, 'message', '') or str(err)\n"
                "        print(f'STREAMLIT CRASH: {msg}\\n{stack}', file=sys.stderr)\n"
                "        sys.exit(1)\n"
                "except Exception as e:\n"
                "    print(f'STREAMLIT EXECUTION ERROR: {type(e).__name__}: {e}', file=sys.stderr)\n"
                "    sys.exit(1)\n"
            )
            try:
                r = subprocess.run(
                    [sys.executable, "-c", runner_script],
                    cwd=workdir,
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=timeout,
                    env=env,
                )
                if r.returncode != 0:
                    err_output = f"{r.stdout}\n{r.stderr}".strip()
                    return False, f"[STREAMLIT ENTRYPOINT CRASH in {rel}]:\n{err_output}"
            except subprocess.TimeoutExpired:
                return False, f"[STREAMLIT TIMEOUT in {rel}]: App failed to execute within {timeout} seconds."

        # 2. General Module Import Smoke Test (only for top-level files)
        elif "/" not in rel and "\\" not in rel:
            mod_name = os.path.splitext(rel)[0]
            check_script = (
                "import sys\n"
                "try:\n"
                f"    import {mod_name}\n"
                "except Exception as e:\n"
                "    print(f'IMPORT ERROR: {type(e).__name__}: {e}', file=sys.stderr)\n"
                "    sys.exit(1)\n"
            )
            try:
                r = subprocess.run(
                    [sys.executable, "-c", check_script],
                    cwd=workdir,
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=timeout,
                    env=env,
                )
                if r.returncode != 0:
                    err_output = (r.stderr or r.stdout).strip()
                    return False, f"[MODULE IMPORT CRASH in {rel}]:\n{err_output}"
            except subprocess.TimeoutExpired:
                pass

    return True, ""


def run_tests(repo: str, edits: dict):
    work = prepare_workdir(repo, edits)
    try:
        passed, pytest_out = run_pytest(work)
        if not passed:
            return False, pytest_out

        smoke_passed, smoke_out = run_entrypoint_smoke_tests(work)
        if not smoke_passed:
            return False, f"{pytest_out}\n\n{smoke_out}".strip()

        return True, pytest_out
    finally:
        shutil.rmtree(os.path.dirname(work), ignore_errors=True)
