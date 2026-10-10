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
  * Reject dummy stubs, hollow implementations, or clunky single-shot prompts.
  * Ensure the entrypoint actually runs end-to-end on the user's platform.
  * Audit UI/UX against Section 5 standards (continuous REPL, natural input, clean error recovery).
  * Include clear "HOW TO TEST" and "HOW TO RUN" instructions in the plain-English explanation.

---

## 5. UI/UX & Human-Centered Interaction Standards
Deliverables must feel like polished, modern software rather than primitive homework scripts:

### A. Continuous Interactive Sessions (REPL)
* **Rule**: Never create a tool that asks for input once and terminates immediately.
* **Requirement**: Interactive CLI tools (calculators, managers, converters, search tools) must run in a continuous loop (`while True`) with prompt indicators (e.g. `calc > `, `>>> `) until the user explicitly inputs `exit`, `quit`, or `q`.

### B. Natural, Intuitive Input Syntax (Anti-Clunky Prompts)
* **Calculators & Math Evaluators**:
  * **Strictly Forbidden**: Never build a clunky 1980s numeric menu (e.g. "Select: 1. Add, 2. Sub... Enter num1: ... Enter num2: ...").
  * **Requirement**: Accept natural mathematical expressions directly (e.g. `2 + 3 * 4`, `(10 - 2) / 4`, `sqrt(16)`, `ans * 2`).
  * Support running memory (`ans` keyword to chain calculations).
  * Provide a `help` or `?` command listing available operators and built-in functions.
* **Menu & Command Tools**: Support both short command aliases (`ls`, `add`, `rm`) and numeric shortcuts.

### C. Visual Polish, Banners & ANSI Styling
* **Welcome Banner**: Print a clean ASCII/Unicode header banner on launch with tool name, version, and quick commands (`help`, `clear`, `quit`).
* **ANSI Color Highlights**: Use cross-platform ANSI escape codes for readability:
  * Cyan/Blue: Prompts and headers (`\033[36m`).
  * Green: Successful results, calculated answers, confirmed actions (`\033[32m`).
  * Yellow: Warnings, help hints, running memory (`\033[33m`).
  * Red: User errors (`\033[31m`).
  * Reset: Reset styles after every print (`\033[0m`).

### D. Graceful Error Recovery (Zero Crashes)
* Never let user typos or bad math (e.g. division by zero, mismatched parentheses, unknown variables) crash the program with a raw Python stack trace.
* Catch exceptions gracefully, display a user-friendly colored error message (e.g. `Error: Division by zero`), and continue the interactive session seamlessly.

### E. Native Graphical UI Option (`tkinter`)
* When the user requests a graphical desktop app, visual calculator, or windowed dashboard:
  * Use Python's built-in `tkinter` module (Standard Library, cross-platform, 0 pip dependencies).
  * Concur with Dual-Contract: Core backend logic classes are pure and tested headlessly with pytest; `tkinter` handles the window, button grids, and display under `if __name__ == '__main__':`.


