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

### E. Native Desktop GUI Standard (`tkinter.ttk`)
* **When to Use**: Desktop utilities, native windowed calculators, interactive dashboards, or when the user requests a "GUI", "desktop app", or "window".
* **Technology**: Built-in Python Standard Library `tkinter` and `tkinter.ttk` (Zero extra pip installs, cross-platform).
* **Architecture & Separation**:
  * **Core Backend Logic**: Pure classes/functions (`Calculator`, `TaskManager`, etc.) completely decoupled from GUI code, enabling 100% headless automated verification with `pytest`.
  * **Presentation Layer**: GUI classes or functions using `tkinter.ttk` widgets (themed buttons, entries, labels, frames).
  * **Mainloop Guard**: Blocking GUI loops (`root.mainloop()`) MUST ONLY execute under `if __name__ == '__main__':` or inside a dedicated `launch()` function. Tests must NEVER trigger `root.mainloop()`.
* **Visual Polish & Styling**:
  * Use `ttk.Style` with modern themes (`clam`, `alt`, or native OS) for polished, non-dated controls.
  * Generous padding (`padx=5, pady=5`), consistent font hierarchies, and responsive grid layouts (`columnconfigure`, `rowconfigure`).
  * Display screens: Bold, right-aligned monospace font for outputs, history labels, and error messages.
  * Full Keyboard Support: Bind keyboard shortcuts (`<Return>`, `<Escape>`, `<BackSpace>`, standard operators) alongside clickable mouse buttons.

### F. Modern Web Application Standard (`streamlit`)
* **When to Use**: Web apps, browser dashboards, analytical tools, or when the user requests a "web app", "browser UI", or "streamlit".
* **Technology**: `streamlit` (standard in MASEDA stack and requirements.txt).
* **Architecture & Separation**:
  * **Core Backend Logic**: Pure computational and data functions in a standalone module (or cleanly separated within the file), fully testable with `pytest` without invoking Streamlit runtime.
  * **Presentation Layer**: Streamlit page layout driven by `st.*` components.
* **Visual Polish & Layout Standards**:
  * Call `st.set_page_config(page_title="...", page_icon="...", layout="centered")` at the very top.
  * Modern card containers using `with st.container(border=True):` to group related controls.
  * Responsive multi-column button grids: `cols = st.columns(4)` for compact, ergonomic layouts.
  * Visual metrics: `st.metric(label="Current Value", value=...)` for high-impact visual feedback.
  * State management: Use `st.session_state` to store calculation history, variables, and themes across user interactions.
  * Collapsible sections: Use `with st.expander("History & Details"):` for secondary information.
  * Run Command: Launched via `streamlit run <file>.py`.

### G. Operational Contract Selection Matrix
* **Explicit Request**: If the user explicitly asks for "GUI / desktop", produce `tkinter.ttk`. If they ask for "web / streamlit", produce `streamlit`. If they ask for "CLI / terminal", produce an interactive REPL.
* **General Request** (e.g. "build a calculator application", "create a note manager"): Default to either a Modern Tkinter Desktop GUI or Streamlit Web App, while always maintaining the pure backend logic layer tested with `pytest`. Include explicit instructions in the Reviewer user explanation on how to run the GUI/web app.


