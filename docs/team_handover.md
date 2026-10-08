# MASEDA: Team Onboarding & Project Handover Document

Welcome to **MASEDA** (**M**ulti-**A**gent **S**oftware **E**ngineering **D**evelopment **A**ssistant). This document provides a complete briefing on what has been implemented so far, the system architecture, how to run and test it locally, and the roadmap for remaining work.

---

## 1. Project Overview & Vision
MASEDA is an autonomous multi-agent coding companion. When a user provides a coding task on a target Python repository, specialized agents collaborate across distinct phases:
- **Planner Agent**: Analyzes repository structure, determines affected files, and creates an execution plan.
- **Coder Agent**: Writes complete replacement files (generating clean git diffs via `difflib`).
- **Test Runner (Sandbox)**: Validates Python syntax using AST, writes to an isolated workspace, and executes pytest test suites.
- **Reviewer Agent**: Evaluates test outcomes and diffs. On failure, diagnoses root causes and generates targeted fixes; on pass, verifies the solution meets task requirements without shortcuts.
- **Feedback Loop**: Routes actionable feedback back to the Coder for iterative refinement (up to `MAX_ITERS`).

A primary academic goal of the project is to **evaluate whether Retrieval-Augmented Generation (RAG) over the codebase improves patch success rates, token efficiency, and correctness**.

---

## 2. Technology Stack & Directory Structure
- **Language**: Python 3.11+
- **Agent Orchestration**: **LangGraph** (Stateful cyclic directed graphs)
- **Model Gateway**: **LiteLLM** (Unified access to Gemini, OpenAI, Claude, local models)
- **RAG & Search**: **ChromaDB** (Dense embeddings) + **Rank-BM25** (Sparse keyword retrieval)
- **Testing & Benchmarks**: **pytest** (100% offline unit tests) + Custom SWE-bench style evaluation harness
- **UI & Sandboxing**: Streamlit UI (Day 6) + Docker sandbox (Day 6)

### Ownership Areas (`AGENTS.md`)
- `app/agents/` — Planner, Coder, Reviewer agents (*Orchestration owner*)
- `app/graph.py`, `app/state.py`, `app/llm.py` — Workflow graph, shared state, model interface (*Orchestration owner*)
- `app/tools/` — File safety, unified diffs, AST syntax validator, sandbox runner (*Tools owner*)
- `app/rag/` — AST chunking, embeddings, Chroma vector store, hybrid BM25 (*RAG owner*)
- `evaluation/` — 20-task benchmark suite, runner, LaTeX reporting (*Evaluation owner*)
- `app/ui/` — Streamlit interactive application (*UI owner*)

---

## 3. What Has Been Completed So Far

### Day 1: Core Skeleton & Resilient Foundations
- **LangGraph Architecture**: Shared `State` (`TypedDict`) tracking `iteration`, `plan`, `edits`, `diff`, `tokens`, `cost`, and `latency`.
- **Defensive LLM Gateway (`app/llm.py`)**:
  - Regex markdown code-fence extractor (```` ```json...``` ````) handling conversational preambles.
  - Automatic trailing-comma repair in JSON objects and lists.
  - Error translation for rate limits (429), timeouts, and auth errors.
- **Security & Sandbox Basics (`app/tools/files.py`, `sandbox.py`)**:
  - Strict path traversal guards (`safe_path()`) preventing `../` escapes.
  - Isolated tempdir copy for testing with scrubbed environment variables (protecting API keys).
  - Explicit `PYTHONPATH` injection and pytest exit code 5 diagnostics.
- **CLI Instrumentation (`app/main.py`)**: Real-time summary reporting tokens, cost, runtime, and diffs.

### Day 2: Reviewer Agent, Guardrails & 20-Task Benchmark
- **Dedicated Reviewer Agent (`app/agents/reviewer.py`)**:
  - Replaced basic boolean checks with intelligent JSON diagnostics (`approved`, `summary`, `feedback`, `suggested_fixes`).
  - Integrated into LangGraph: `planner` $\rightarrow$ `coder` $\rightarrow$ `run_tests` $\rightarrow$ `reviewer` $\rightarrow$ conditional loop.
- **AST Syntax Pre-validation (`ast.parse`)**:
  - Inspects code syntax prior to running pytest; catches `SyntaxError` instantly with line/column numbers.
- **Repeat-Edit Circuit Breaker**:
  - Detects if the Coder repeats identical code across failed attempts. Injects warnings on repeat 1, and halts on repeat 2 to avoid token burn.
- **20-Task Benchmark Suite (`evaluation/tasks.json` & `evaluation/bench_repo/`)**:
  - Multi-module target repository with Math, Strings, Collections, Geometry, and Validators.
  - **SWE-bench style failing setup edits (`setup_edits`)**: Guarantees tests fail before the agent begins (`[PRE:FAIL]`), proving genuine problem resolution.
- **Evaluation Harness (`evaluation/run_eval.py`)**:
  - Automated runner supporting category breakdowns (`Bugfix`, `Feature`, `Edge_Case`, `Multi_File`).
  - **Dissertation LaTeX Table Exporter**: Automatically writes ready-to-publish tables to `evaluation/results/baseline_report.md`.
  - **Zero-Cost Mock Mode (`--mock`)**: Allows running all 20 benchmark tasks offline in seconds.
- **Unit Test Coverage**: **15 of 15 unit tests passing completely offline** (`pytest -q`).

---

## 4. Roadmap: What We Will Be Doing Next

| Day | Goal | Deliverable & Done-When Criteria |
|:---:|:---|:---|
| **Day 3** | **RAG Ingestion** | AST chunking by function & class, embeddings, Chroma vector store. Done when retrieval recall is 80%+ on test queries. |
| **Day 4** | **Hybrid RAG Integration** | Combine BM25 keyword search with Chroma dense search; add `--rag` toggle switch into Planner and Coder. |
| **Day 5** | **Benchmark Experiments** | Run comparative study (No-RAG vs Dense RAG vs Hybrid RAG, 3 runs each); generate matplotlib charts and failure analysis. |
| **Day 6** | **Streamlit UI & Docker Sandbox** | Interactive web app (task input, live agent traces, diff review, apply changes) and Docker container isolation. |
| **Day 7** | **Dissertation Draft** | Write methodology, benchmark results, threat to validity, and decision logs. |
| **Day 8** | **Final Submission Polish** | Demo recording, presentation slides, and viva Q&A rehearsal. |

---

## 5. How to Set Up & Run the Project Locally

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/NightMare27-hub/maseda.git
cd maseda
git checkout feature/day2-reviewer-and-eval
python -m venv .venv

# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Run Offline Unit Tests (Instant & Free)
```bash
pytest -v
```
*(All 15 tests should pass without requiring any API key).*

### 3. Run the 20-Task Benchmark in Mock Mode
```bash
python evaluation/run_eval.py --mock
```
Check the generated report in `evaluation/results/baseline_report.md`.

### 4. Run with a Live AI Model
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Add your model and API key:
   ```ini
   MODEL=gemini/gemini-2.5-flash
   GEMINI_API_KEY=your_key_here
   # Or MODEL=gpt-4o-mini with OPENAI_API_KEY=your_key_here
   ```
3. Run a live task:
   ```bash
   python -m app.main --repo evaluation/toy_repo --task "Implement divide(a, b) in calculator.py. It must raise ValueError when b is zero." --apply
   ```

---

## 6. Team Collaboration Rules (`AGENTS.md`)
1. **Never commit `.env` or API keys**. `.gitignore` is configured, but always double check `git status`.
2. **Work on your own branch** (`feature/<your-feature-name>`). Never push directly to `main`.
3. **Open a Pull Request** on GitHub for code review before merging into `main`.
4. **Structured JSON only**: Agents communicate via fixed-field JSON schemas, never unstructured text.
5. **Always run `pytest -q`** before opening a PR to ensure no regressions.
6. **Log architectural decisions** in `docs/decisions.md` and AI usage in `docs/ai_usage_log.md`.
