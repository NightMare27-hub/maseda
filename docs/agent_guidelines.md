# MASEDA Agent Guidelines & Engineering Standards

These standards govern how Planner, Coder, and Reviewer agents analyze tasks, generate software, and evaluate deliverables.

---

## 1. Dual-Contract Architecture
Every user request requires two distinct contracts:

### A. The Verification Contract (Machine-Facing)
* **Goal**: Verifiable correctness under automated evaluation (`pytest`).
* **Implementation**: Classes, functions, and algorithms must be modular, pure, and testable programmatically in an automated headless sandbox.
* **Constraints**: No blocking interactive calls (`input()`), no infinite loops, and no unmocked network I/O inside test suites.

### B. The Operational Contract (Human-Facing)
* **Goal**: Real-world usability for the end user.
* **Implementation**: If the task requests a runnable tool, CLI, or game, provide a fully functional entrypoint under `if __name__ == '__main__':`.
* **Anti-Stubbing Policy**: Never replace interactive or complex behavior with a single static print, dummy stub, or hardcoded return value just to make the test runner pass.

---

## 2. Zero-Friction Cross-Platform Rule (Zero Extra Steps)
Deliverables must run out-of-the-box on the user's host operating system without requiring manual third-party package installations or OS emulators:

### A. Windows Console & Keyboard Input
* Standard Windows Python installations do not include Unix `curses`.
* **Requirement**: When creating interactive CLI tools or games on Windows:
  * Use Python's built-in `msvcrt` module (`msvcrt.getch()`, `msvcrt.kbhit()`) for real-time keypresses, or
  * Use universal standard input (`input()`) in a clean loop.
  * **Strictly Forbidden**: Never emit a fallback that prints `"curses is not installed, install windows-curses"` and terminates.

### B. Linux & macOS Console
* Use `curses`, `termios`, or standard `input()` gracefully using `sys.platform` checks:
  ```python
  import sys
  if sys.platform == "win32":
      import msvcrt
      # Native Windows interactive input
  else:
      # Native Unix interactive input
  ```

---

## 3. Dependency & Standard Library Preference
* Always prefer Python's Standard Library (`math`, `json`, `urllib`, `dataclasses`, `pathlib`, `random`, `msvcrt`) over external packages.
* Avoid introducing uninstalled external dependencies (`pygame`, `requests`, `numpy`, `windows-curses`) unless the repository or user explicitly mandates them.

---

## 4. Dual-Gate Reviewer Verification
The Reviewer evaluates two independent gates before approving any change:
* **Gate 1 (Automated Verification)**: All unit tests must pass cleanly in the sandbox (`pytest == 0`).
* **Gate 2 (Operational Fulfillment & Usability)**: The code must deliver genuine human usability:
  * Reject dummy stubs or hollow implementations.
  * Ensure the entrypoint actually runs end-to-end on the user's platform.
  * Include clear "HOW TO TEST" and "HOW TO RUN" instructions in the plain-English explanation.

