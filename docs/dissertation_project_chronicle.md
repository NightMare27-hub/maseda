# MASEDA Dissertation Project Chronicle: Days 1 to 4
**Comprehensive Architectural Retrospective, Technical Audit & Dissertation Baseline**
*Project: Multi-Agent Software Development Assistant (MASEDA)*
*Document Version: 1.0 — Target Length Context: Baseline Source for 40–60 Page Academic Thesis*

---

## 1. Executive Summary & Research Foundation

### 1.1 The Research Problem
Modern Large Language Models (LLMs) demonstrate significant code generation capabilities, yet single-prompt generation degrades rapidly when applied to multi-file software repositories. Key failure modes include:
1. **Context Window Exhaustion & Dilution**: Ingesting entire codebases inflates token costs and drowns needle-in-a-haystack logic within boilerplate.
2. **Hallucination of Non-Existent Interfaces**: LLMs invent function signatures or import nonexistent modules rather than conforming to established repository contracts.
3. **Goodhart's Law & Hollow Optimization**: When evaluated solely against automated unit test suites (`pytest`), agents frequently stub out interactive user interfaces, disable exception handlers, or replace complex rendering loops with static dummy prints to achieve a deceptive "all-green" test status.

### 1.2 The MASEDA Hypothesis
The **Multi-Agent Software Development Assistant (MASEDA)** investigates whether decomposing software engineering into specialized cognitive agents (**Planner**, **Coder**, **Reviewer**) coordinated via a cyclic directed graph (**LangGraph**), combined with **Syntax-Aware Hybrid Retrieval-Augmented Generation (AST-based RAG)** and **Dual-Contract Verification**, systematically outperforms traditional single-agent and non-RAG baselines across functional accuracy, token efficiency, convergence speed, and human usability.

---

## 2. Day-by-Day In-Depth Technical Chronicle

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 MASEDA TIMELINE OVERVIEW                               │
├─────────────────┬──────────────────┬──────────────────┬─────────────────┬──────────────┤
│      DAY 1      │      DAY 2       │      DAY 3       │      DAY 4      │    DAY 5     │
│  Core Workflow  │ Reviewer Agent,  │ Standalone RAG:  │   Hybrid RAG    │ Comparative  │
│  & Orchestration│ Guardrails, and  │ AST Chunking,    │ Agent Ingestion,│ Experiments, │
│    Foundation   │ 20-Task Benchmark│ Chroma, and BM25 │ Dual-Contract   │ LaTeX & Plots│
└─────────────────┴──────────────────┴──────────────────┴─────────────────┴──────────────┘
```

---

### DAY 1: Architectural Foundation, Core Workflow & Agent Orchestration

#### 1. What We Were Meant to Do (Planned Scope)
* Initialize project repository and environment according to `AGENTS.md`.
* Construct a minimal multi-agent workflow using LangGraph consisting of a **Planner** and a **Coder**.
* Create a shared `State` dictionary representing workflow progression.
* Implement a unified LLM interface wrapping LiteLLM.
* Implement basic filesystem tools (read, write, list) and a sandboxed test execution harness (`pytest`).
* Validate end-to-end execution against a minimal toy repository (`evaluation/toy_repo`).

#### 2. What We Actually Did (Engineering Execution)
* **Resilient Multi-Tier JSON Parsing (`app/llm.py`)**:
  LLMs frequently output markdown fences (` ```json `), explanatory preamble, or trailing commas before closing braces. We engineered a robust four-tier extraction engine:
  1. Strict `json.loads()`.
  2. Markdown code block regex extraction (`r"```(?:json)?\s*([\s\S]*?)\s*```"`).
  3. Outermost brace slicing (`text.find("{")` to `text.rfind("}")`).
  4. Trailing comma sanitization regex (`r",\s*([\]}])"`).
* **Comprehensive Metrics Instrumentation (`app/state.py` & `app/logger.py`)**:
  Instrumented `State` to accumulate wall-clock latency, input/output token counts, and USD API expenditures across all node iterations, logging JSONL audit events per Rule 6.
* **Deterministic Sandboxed Execution (`app/tools/sandbox.py`)**:
  Constructed `run_pytest()` with strict subprocess isolation, explicit `PYTHONPATH` injection (resolving sibling imports), a 30-second hard execution ceiling, and diagnostic categorization for exit code 5 (zero tests collected).
* **Unified Diff Engine & Safety Switch (`app/main.py`)**:
  Implemented `difflib.unified_diff` inspection in CLI. Changes run in preview mode by default; disk writes occur only when the explicit `--apply` flag is supplied and tests succeed.
* **Baseline Offline Unit Tests (`tests/test_pipeline.py`)**:
  Constructed 10 deterministic unit tests covering tool safety, path traversal prevention, JSON resilience, and execution flow.

#### 3. Files, Agents, Guardrails & Artifacts Created
* **Agents**: `app/agents/planner.py`, `app/agents/coder.py`.
* **Core Orchestration**: `app/graph.py` (StateGraph compilation), `app/state.py`, `app/llm.py`, `app/logger.py`.
* **Execution Tools**: `app/tools/files.py` (`safe_path`, `read_file`, `apply_edits`), `app/tools/sandbox.py` (`run_pytest`).
* **CLI & Targets**: `app/main.py`, `evaluation/toy_repo/` (`calculator.py`, `test_calculator.py`).
* **Test Suite**: `tests/test_pipeline.py` (10 tests passing).
* **Guardrails**:
  - `safe_path()` directory traversal guardrail (`..` rejection).
  - Subprocess execution timeout ceiling (30s).
  - Explicit non-destructive dry-run by default (`--apply` guardrail).

#### 4. Technology Stack & Depth of Utilization
* **LangGraph (v0.2+)**: Constructed sequential `StateGraph` with typed shared state, compiling state transformations into runnable graphs.
* **LiteLLM**: Abstracted provider calls; leveraged `completion_cost()` for financial metrics.
* **Python Subprocess & Difflib**: Subprocess management for test runner; unified line diff generation.
* **Pytest**: Automated test framework utilized both internally for testing MASEDA and externally as the agent validation engine.

#### 5. Critical Challenges & Resolutions
* *Challenge*: The model outputted explanatory conversational text along with JSON, crashing naive deserializers.
  *Resolution*: Multi-tier regex and bracket extraction pipeline in `parse_json()`.
* *Challenge*: Tests failed inside subprocess due to `ModuleNotFoundError` for local modules.
  *Resolution*: Explicit injection of the repository root into `env["PYTHONPATH"]`.

#### 6. What More Could Have Been Done (Day 1 Limitations)
* Process sandboxing relied on OS subprocesses rather than Docker containerization.
* The agent loop was purely linear (`planner -> coder -> test`); no iterative critique or self-correction mechanism existed.

---

### DAY 2: The Reviewer Agent, Guardrails & 20-Task Benchmark Suite

#### 1. What We Were Meant to Do (Planned Scope)
* Introduce an intelligent **Reviewer Agent** to eliminate binary pass/fail limitations.
* Convert the linear workflow into an iterative feedback cycle (`planner -> coder -> test -> reviewer -> loop`).
* Construct an evaluation benchmark capable of measuring bug fixes, new features, and edge cases.
* Implement an automated evaluation runner (`evaluation/run_eval.py`).

#### 2. What We Actually Did (Engineering Execution)
* **Intelligent Reviewer Agent (`app/agents/reviewer.py`)**:
  Engineered a specialized agent that analyzes task intent, code diffs, and pytest failure logs, outputting structured JSON diagnoses:
  `{"approved": bool, "summary": str, "feedback": str, "suggested_fixes": list[str]}`.
* **Cyclic Directed Graph with Feedback Loops (`app/graph.py`)**:
  Re-architected the state machine. If tests fail or the Reviewer rejects the code, execution routes back to the Coder with accumulated diagnostic feedback for up to 3 iterative attempts.
* **AST Syntax Pre-Validation Guardrail (`ast.parse`)**:
  Integrated abstract syntax tree parsing into the sandbox pipeline. Catches syntax errors (unclosed brackets, invalid indentation) before spawning a pytest subprocess, providing line-and-column diagnostic feedback.
* **Anti-Stagnation & Repeat-Edit Circuit Breaker**:
  Implemented hashing of file edits across consecutive iterations. If the Coder generates an identical failing patch twice, the circuit breaker halts execution to eliminate infinite loops and token burn.
* **20-Task Academic Benchmark Suite (`evaluation/tasks.json` & `evaluation/bench_repo/`)**:
  Constructed a modular multi-file repository (`bench_repo`) spanning 5 functional domains:
  - `math_ops.py` (Math & Numerical Algorithms)
  - `string_ops.py` (Text & String Transformations)
  - `collections.py` (Data Structures & Functional Utilities)
  - `geometry.py` (2D Spatial Coordinates & Classes)
  - `validators.py` (Regex, Formatting & Email Validation)
  Curated 20 realistic tasks across 4 categories: **Bugfix** (4), **Feature** (10), **Edge_Case** (4), **Multi_File** (2).
* **SWE-bench Style Pre-Patch Verification (`setup_edits`)**:
  Engineered failing pre-conditions (`setup_edits`) injected before task execution. Confirms tests fail initially (`[PRE:FAIL]`), proving the agent resolved a genuine issue rather than asserting an already-green repository.
* **Dissertation LaTeX Table Exporter (`evaluation/run_eval.py`)**:
  Engineered an evaluation harness supporting `--mock` (instant offline zero-cost simulation) and automated generation of thesis-ready LaTeX tables (`\begin{table}`, `\caption`, category summaries).
* **Unit Test Expansion**: Increased test suite to 15 offline unit tests (`tests/test_evaluation.py`).

#### 3. Files, Agents, Guardrails & Artifacts Created
* **Agents**: `app/agents/reviewer.py`.
* **Benchmark Core**: `evaluation/bench_repo/` (5 source modules, 5 test suites), `evaluation/tasks.json`, `evaluation/build_tasks.py`.
* **Evaluation Runner**: `evaluation/run_eval.py`, `evaluation/results/baseline_report.md`.
* **Test Suite**: `tests/test_evaluation.py` (5 new tests, 15 total).
* **Guardrails**:
  - AST Pre-Execution Syntax Validator.
  - Stagnation / Repeat-Edit Circuit Breaker (halts on identical consecutive edits).
  - Iteration Ceiling Guardrail (terminates at `iteration >= 3`).

#### 4. Technology Stack & Depth of Utilization
* **LangGraph Cyclic Graphs**: Implemented conditional routing using `add_conditional_edges()` based on reviewer approval and iteration count.
* **Python `ast` Module**: Static analysis parsing Python code into AST nodes without execution.
* **SWE-bench Methodology**: Adopted benchmark standards requiring pre-execution verification.
* **LaTeX Generator**: Dynamic text formatting generating publication-ready tables.

#### 5. Critical Challenges & Resolutions
* *Challenge*: The model got stuck in repetitive loops outputting the same broken fix when encountering stubborn test failures.
  *Resolution*: Engineered the repeat-edit circuit breaker in `coder.py` comparing hash signatures of proposed file edits.
* *Challenge*: Running evaluation on live LLMs was slow and expensive for CI/CD and teammate testing.
  *Resolution*: Built the `--mock` flag in `run_eval.py` utilizing golden solutions for instant, free verification.

#### 6. What More Could Have Been Done (Day 2 Limitations)
* The agent lacked codebase search capabilities. On multi-file tasks, Planner had to guess which files to modify based solely on filenames.
* Prompts dumped entire files into Coder context, leading to high token usage on larger modules.

---

### DAY 3: Standalone Syntax-Aware RAG Engine (AST Chunking, Chroma & BM25)

#### 1. What We Were Meant to Do (Planned Scope)
* Construct a standalone codebase indexing and retrieval engine tailored specifically for Python repositories.
* Implement AST-based semantic chunking breaking code by function and class definitions rather than arbitrary token windows.
* Ingest code chunks into Chroma vector database.
* Implement BM25 keyword search to capture exact identifier matches.
* Combine dense and sparse retrieval into a hybrid retrieval engine.
* Evaluate retrieval recall on target benchmark repositories.

#### 2. What We Actually Did (Engineering Execution)
* **Syntax-Aware AST Chunking Engine (`app/rag/chunk.py`)**:
  Engineered an AST visitor that parses Python files into granular logical blocks:
  - Preserves class hierarchy (e.g. `Rectangle.area` identifies parent class `Rectangle`).
  - Retains function decorators (`@property`, `@staticmethod`, `@pytest.fixture`).
  - Attaches metadata: file path, line numbers (`start_line`, `end_line`), token estimates (`len(code)//4`), line counts, and character counts.
  - Generates deterministic, human-readable chunk IDs: `<relpath>::<class>.<method>` or `<relpath>::<function>`.
* **AST SyntaxError Fallback Guardrail**:
  If a repository file contains invalid syntax (e.g., during active bugfixing), the chunker gracefully falls back to emitting whole-module chunks rather than crashing indexing.
* **Offline Deterministic Embedding Layer (`app/rag/embed.py`)**:
  Created `FakeEmbedder` using deterministic character-hashing vectors for 100% offline, zero-network unit testing. Created `ChromaEmbeddingAdapter` to bridge custom embedders to Chroma.
* **Chroma Vector Ingestion (`app/rag/ingest.py`)**:
  Constructed indexing pipeline filtering out `.git`, `__pycache__`, `.venv`, and `.env`, upserting documents and structured metadata into Chroma collections.
* **Multi-Modal Retrieval Engine (`app/rag/retrieve.py`)**:
  Implemented three retrieval strategies:
  1. **Dense Semantic Retrieval**: Vector cosine distance via Chroma. Added safety clamping (`min(k, collection.count())`) to prevent Chroma crashes on small repositories.
  2. **BM25 Keyword Retrieval**: Tokenized lexical matching via `rank_bm25`. Enhanced with CamelCase and snake_case sub-token splitting (`formatDate` -> `format`, `date`).
  3. **Reciprocal Rank Fusion (RRF) Hybrid Retrieval**: Blends dense and BM25 rankings without score normalization:
     $$RRF(d) = \sum_{m \in \{dense, bm25\}} \frac{1}{60 + \text{rank}_m(d)}$$
  4. **Scoped Metadata Filtering (`where`)**: Enables filtered retrieval by symbol kind (`function`, `class`, `method`).
* **Academic Information Retrieval Benchmark Runner (`evaluation/eval_rag.py`)**:
  Constructed an IR evaluation runner testing 15 realistic developer queries against `bench_repo`, measuring:
  - **Recall@1**: Dense: 93.3%, BM25: 66.7%, Hybrid: 73.3%
  - **Recall@5**: Dense: 100.0%, BM25: 86.7%, Hybrid: 100.0%
  - **MRR (Mean Reciprocal Rank)**: Dense: 0.9667, BM25: 0.7278, Hybrid: 0.8356
  - Exports LaTeX tables directly to `evaluation/results/rag_retrieval_report.md`.
* **Interactive Terminal Search CLI (`app/rag/search.py`)**:
  CLI utility allowing engineers to query repositories with `--mode {dense,bm25,hybrid}` directly from the terminal.
* **Test Suite Expansion**: Added 8 offline unit tests in `tests/test_rag.py` (23 total tests).

#### 3. Files, Agents, Guardrails & Artifacts Created
* **RAG Pipeline**: `app/rag/chunk.py`, `app/rag/embed.py`, `app/rag/ingest.py`, `app/rag/retrieve.py`, `app/rag/search.py`.
* **Evaluation & Reports**: `evaluation/eval_rag.py`, `evaluation/results/rag_retrieval_report.md`.
* **Test Suite**: `tests/test_rag.py` (8 new tests, 23 total).
* **Guardrails**:
  - `SyntaxError` Chunking Fallback.
  - Chroma Count Clamping (prevents `ValueError` when `k > total_chunks`).
  - Secret & Virtualenv Ignore Rules (never indexes `.env`, `.venv`, `.git`).

#### 4. Technology Stack & Depth of Utilization
* **ChromaDB**: In-memory and persistent vector storage with metadata querying.
* **ONNX Runtime (`all-MiniLM-L6-v2`)**: Local neural embedding generation (384 dimensions).
* **Rank-BM25 (`BM25Okapi`)**: Probabilistic lexical ranking.
* **Reciprocal Rank Fusion (RRF)**: Rank aggregation algorithm for combining sparse and dense scores.

#### 5. Critical Challenges & Resolutions
* *Challenge*: Chroma threw fatal exceptions when querying `k=5` on repos with fewer than 5 total chunks.
  *Resolution*: Clamped query limit to `min(k, collection.count())` in `app/rag/retrieve.py`.
* *Challenge*: BM25 failed to match queries like "format date" against CamelCase functions like `formatDate`.
  *Resolution*: Built regex-based CamelCase word splitting in `_tokens()` in `app/rag/retrieve.py`.

#### 6. What More Could Have Been Done (Day 3 Limitations)
* The RAG engine remained completely decoupled from the agent state machine (agents were not yet consuming retrieved chunks).
* Embeddings were single-granularity; hierarchical summarization was not implemented.

---

### DAY 4: Hybrid RAG Agent Integration, System Resilience & Dual-Contract Architecture

#### 1. What We Were Meant to Do (Planned Scope)
* Connect the Day 3 RAG engine into the Planner and Coder agents via a `--rag` toggle switch.
* Support `--rag-mode {hybrid, dense, bm25}` in `main.py` and `run_eval.py`.
* Ensure 100% backward compatibility when `--rag` is omitted.
* Validate end-to-end multi-agent execution with retrieved context.

#### 2. What We Actually Did (Engineering Execution)
* **RAG-Augmented Shared State (`app/state.py`)**:
  Added typed configuration fields: `rag_enabled: bool`, `rag_mode: str`, and `retrieved_chunks: list[dict]`.
* **Symbolic Context Injection in Planner (`app/agents/planner.py`)**:
  When `--rag` is active, Planner queries the codebase and injects matching symbol names, kinds, and line ranges into the prompt under `RELEVANT REPO SYMBOLS (RAG):`. Stores retrieved chunks in `State` to avoid redundant re-indexing in downstream nodes.
* **Budget-Aware Context Packing in Coder (`app/agents/coder.py`)**:
  Coder formats retrieved AST chunks with line numbers and enclosing classes. Enforces a strict context budget ceiling (capped at **3,500 tokens**) using chunk token estimates.
* **AST File Outlining for Large Files**:
  When full files exceed length thresholds, Coder injects top-level AST function/class signatures (`_file_outline()`) instead of blindly truncating source files.
* **System Resilience & Auto-Test Bootstrapping**:
  - When repositories contain zero tests, Planner automatically mandates creating companion test files (`test_<module>.py`).
  - Reviewer detects `ModuleNotFoundError` and exit code 5, providing direct guidance to fall back on Python's Standard Library.
* **Systemic Sandbox Diagnostic Annotations (`app/tools/sandbox.py`)**:
  Annotates cryptic stack traces with actionable guidance:
  - `EOFError` -> `[INTERACTIVE INPUT BLOCKED]`
  - `URLError` / socket errors -> `[OFFLINE SANDBOX]`
  - `pygame.error: No video device` -> `[HEADLESS DISPLAY]`
  - `TimeoutExpired` -> `[SANDBOX TIME LIMIT EXCEEDED]`
* **Plain-English User Explanations (`app/agents/reviewer.py`)**:
  Reviewer generates non-technical explanations (`user_explanation`) translating technical diagnostics into accessible language for end users.
* **Dynamic Gemini Model Cascade (`app/llm.py`)**:
  Integrated Google Generative Language API model discovery. If a model encounters 503, 429, 404, or timeouts, LiteLLM dynamically cascades to similar versioned models (`gemini-3.8-flash` -> `3.7-flash` -> `3.6-flash` -> `3.5-flash-lite`).
* **Real-Time LangGraph Node Progress Streaming (`app/graph.py`)**:
  Implemented streaming graph execution (`g.stream()`), displaying real-time console banners (`[PLANNER]`, `[CODER]`, `[SANDBOX]`, `[REVIEWER]`) along with upfront architectural approach strategies.
* **Dual-Contract Architecture & Dual-Gate Reviewer**:
  - **Planner**: Mandates both a `logic_contract` (for automated pytest verification) and an `operational_contract` (runnable CLI/loop for human users).
  - **Coder**: Mandated to construct runnable entrypoints under `if __name__ == '__main__':`; strictly forbidden from emitting dummy prints or hollow stubs.
  - **Reviewer**: Evaluates Gate 1 (automated test pass) AND Gate 2 (human usability audit). Rejects code if operational loop is broken, even if 100% of unit tests pass.
* **Externalized Engineering Standards (`docs/agent_guidelines.md`)**:
  Replaced hardcoded prompts with centralized Markdown guidelines ingested dynamically via `load_guidelines()`. Codified the Zero-Friction Cross-Platform Rule (native Windows `msvcrt.getch()` / `kbhit()` support).
* **Generation Timeout Resolution**:
  Extended `timeout` in `_complete()` from 30s to **90s**, eliminating false-alarm cascade failovers during large file generation.
* **Autonomous Windows Snake Game Solution (`evaluation/snake_repo/`)**:
  MASEDA autonomously implemented a flicker-free interactive terminal Snake game in Windows console using `msvcrt` and ANSI cursor positioning, passing all 11 unit tests.
* **Offline Test Isolation Hardening**:
  Mocked remote retrieval in `test_run_task_with_rag_end_to_end` to eliminate remote ONNX downloads over SSL, preventing test freezes on fresh teammate environments.
* **Unit Test Expansion**: Full test suite elevated to **37 unit tests passing 100% offline in ~20 seconds**.

#### 3. Files, Agents, Guardrails & Artifacts Created
* **Agents Updated**: `app/agents/planner.py`, `app/agents/coder.py`, `app/agents/reviewer.py`.
* **State Machine & Wrappers**: `app/graph.py`, `app/state.py`, `app/llm.py`.
* **Engineering Standards**: `docs/agent_guidelines.md`.
* **Interactive Target Repo**: `evaluation/snake_repo/` (`snake.py`, `test_snake.py`).
* **Documentation**: `docs/day4_implementation_plan.md`, `docs/decisions.md` (24 entries), `docs/ai_usage_log.md` (17 entries).
* **Test Suite**: `tests/test_day4_rag_integration.py` (14 new tests, 37 total).
* **Guardrails**:
  - Dual-Gate Review Protocol (Gate 1: Tests, Gate 2: Usability).
  - Context Token Budget Ceiling (3,500 tokens).
  - Dynamic API Model Failover Cascade.
  - Offline Test SSL Download Isolation.

#### 4. Technology Stack & Depth of Utilization
* **LangGraph**: Real-time event streaming (`g.stream()`) and typed state passing.
* **Google Generative Language API**: Dynamic model capability discovery via REST.
* **Windows Console API (`msvcrt`)**: Non-blocking keyboard buffer polling (`kbhit()`, `getch()`) for real-time game loops.
* **VT100 / ANSI Terminal Sequences**: Cursor repositioning (`\033[H`) and visibility toggling (`\033[?25l`) for flicker-free terminal rendering.

#### 5. Critical Challenges & Resolutions
* *Challenge*: 30-second timeout in `_complete()` caused Coder calls to abort while generating 300+ line files, triggering cascading retries across models and burning 90,000+ tokens.
  *Resolution*: Extended completion timeout to 90 seconds in `app/llm.py`.
* *Challenge*: Teammate experienced a 6-minute freeze in `ssl.py:1136` during `pytest -q`.
  *Resolution*: Chroma's `DefaultEmbeddingFunction` was attempting to download an 80MB ONNX model from AWS S3 in `test_run_task_with_rag_end_to_end`. Mocked `retrieve.hybrid` to guarantee 100% offline test execution.
* *Challenge*: Models stubbed out interactive loops to ensure headless tests passed (Goodhart's Law).
  *Resolution*: Architected the Dual-Contract / Dual-Gate protocol and externalized guidelines in `docs/agent_guidelines.md`.

#### 6. What More Could Have Been Done (Day 4 Limitations)
* Context retrieval was static (top-5 chunks selected once during planning). If Coder discovered it needed additional helper functions during generation, it could not issue secondary search queries.
* Agent guidelines are currently injected in full (~60 lines) rather than dynamically retrieved via Policy-RAG.

---

## 3. Technology Stack & Utilization Matrix

| Technology | Purpose in MASEDA | Depth of Utilization | Academic Justification for Thesis |
|---|---|---|---|
| **Python 3.11 / 3.14** | Core programming language | Standard Library (ast, difflib, subprocess, urllib, msvcrt, dataclasses) | Demonstrates standard library preference over bloated external dependencies. |
| **LangGraph (v0.2+)** | Agent orchestration framework | Cyclic `StateGraph`, conditional edges, state reducers, real-time node streaming | Provides deterministic state machine orchestration compared to unconstrained autonomous loops. |
| **LiteLLM** | Unified LLM API gateway | Dynamic model cascade, completion cost tracking, structured JSON enforcement | Enables multi-model failover and precise financial metrics tracking. |
| **ChromaDB** | Vector database for code retrieval | Persistent client, collection upsert, metadata filtering, count clamping | Industry-standard vector store providing fast embedding search. |
| **Rank-BM25** | Lexical keyword retrieval | Custom tokenization with CamelCase and snake_case sub-token splitting | Catches exact identifier and variable matches missed by semantic embeddings. |
| **Reciprocal Rank Fusion** | Hybrid retrieval rank aggregator | Parameter-free rank fusion ($k=60$) | Robust hybrid search without fragile score normalization. |
| **Python AST Module** | Static analysis & code parsing | Syntax pre-validation, function/class chunking, signature file outlines | Eliminates syntax errors before execution; creates semantically intact code chunks. |
| **Pytest** | Automated verification harness | Test discovery, subprocess execution, failure capture, headless sandboxing | Provides objective functional correctness verification (Gate 1). |
| **Windows `msvcrt` & ANSI** | Native interactive console input | Non-blocking key polling (`kbhit`), character extraction (`getch`), ANSI cursor manipulation | Proves cross-platform zero-friction engineering without Unix dependencies on Windows. |

---

## 4. Comprehensive Architectural Inventory

### 4.1 Agent Roster
1. **Planner Agent (`app/agents/planner.py`)**:
   - Decomposes tasks into structured plans (`files`, `steps`, `approach`, `logic_contract`, `operational_contract`).
   - Dynamically ingests repository file listings and top-k retrieved symbols when RAG is active.
   - Enforces automatic test bootstrapping when repositories lack test suites.
2. **Coder Agent (`app/agents/coder.py`)**:
   - Implements full file contents for changed modules.
   - Ingests budgeted AST code chunks (up to 3,500 tokens) and AST file outlines for large files.
   - Strictly conforms to Dual-Contract guidelines; implements runnable entrypoints.
   - Protected by the Repeat-Edit Circuit Breaker against stagnant loops.
3. **Reviewer Agent (`app/agents/reviewer.py`)**:
   - Enforces the Dual-Gate Review Protocol (Gate 1: Automated unit tests; Gate 2: Operational usability).
   - Diagnoses stack traces, exit codes, and missing dependencies, guiding Coder toward Standard Library solutions.
   - Translates technical failures into accessible, plain-English explanations for end users.

### 4.2 Core Safety Guardrails
1. **Directory Traversal Guardrail (`safe_path`)**: Prevents agents from reading or writing outside the repository root.
2. **Dry-Run Non-Destructive Guardrail (`--apply`)**: Changes remain in memory and preview diffs unless `--apply` is explicitly passed and tests succeed.
3. **AST Syntax Pre-Validation Guardrail (`ast.parse`)**: Catches invalid Python syntax before subprocess execution.
4. **Repeat-Edit Circuit Breaker**: Halts execution if the Coder produces identical failing code twice.
5. **Context Budget Ceiling Guardrail**: Caps retrieved code injection at 3,500 tokens to prevent context dilution.
6. **Subprocess Execution Ceiling**: Enforces 30-second time boundaries on sandboxed test runs.
7. **Dynamic Model Failover Cascade**: Automatically routes around 503, 429, and dead endpoints.
8. **Offline Test Isolation Guardrail**: Guarantees test suites execute 100% offline using `FakeEmbedder` and mocked retrievals.
9. **Anti-Stubbing Usability Gate (Gate 2)**: Rejects hollow stubs that pass tests by crippling interactive features.

---

## 5. Architectural Decision Log Summary (24 Formal Decisions)

*From `docs/decisions.md`:*
1. **2026-10-07**: Resilient JSON parser in `app/llm.py` (Multi-tier regex extraction).
2. **2026-10-07**: Cumulative metrics tracking in `State` (Tokens, cost, latency).
3. **2026-10-07**: Explicit `PYTHONPATH` and exit code 5 diagnostic in sandbox.
4. **2026-10-08**: Dedicated `Reviewer` agent in LangGraph state machine.
5. **2026-10-08**: Multi-module `bench_repo` and 20-task benchmark suite.
6. **2026-10-08**: AST Syntax pre-validation before sandbox subprocess execution.
7. **2026-10-08**: Oscillation & Repeat-Edit Circuit Breaker.
8. **2026-10-08**: SWE-bench style failing setup edits (`setup_edits`) and LaTeX table exporter.
9. **2026-10-09**: Standalone RAG ingestion with deterministic chunk IDs.
10. **2026-10-09**: Injectable fake embedder for offline deterministic testing.
11. **2026-10-09**: Reciprocal Rank Fusion (RRF) for hybrid retrieval.
12. **2026-10-09**: SyntaxError fallback & academic IR metrics (Recall@K, MRR).
13. **2026-10-09**: Chroma count guardrail & CamelCase BM25 sub-token expansion.
14. **2026-10-09**: Context budget metadata, scoped filtering (`where`), and search CLI.
15. **2026-10-09**: Hybrid RAG integration into Planner and Coder with `--rag` toggle.
16. **2026-10-09**: Auto-test bootstrapping, Standard Library fallback guidance, and AST file outlines.
17. **2026-10-09**: Systemic sandbox diagnostic hints (EOFError, URLError, Pygame, Timeout).
18. **2026-10-09**: Plain-English user explanations in Reviewer.
19. **2026-10-10**: Dynamic Gemini model cascade & live streaming progress.
20. **2026-10-10**: Dual-Contract Architecture (Logic vs Operational contracts).
21. **2026-10-10**: Dual-Gate Review Protocol (Automated tests vs Usability audit).
22. **2026-10-10**: Externalized Engineering Guidelines in Markdown (`docs/agent_guidelines.md`).
23. **2026-10-10**: Extended 90s LLM timeout for large code file generation.
24. **2026-10-10**: Offline test isolation for end-to-end RAG workflows.

---

## 6. Mapping to the 40–60 Page Dissertation Structure

This chronicle maps directly to the required chapters of the final academic dissertation:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DISSERTATION CHAPTER MAPPING & PAGE TARGETS                     │
├────────────────────────────┬─────────────────────────────┬─────────────────────────────┤
│ Chapter 1: Introduction    │ Chapter 2: Literature Review│ Chapter 3: Methodology      │
│ (5-7 pages)                │ & Theory (8-10 pages)       │ & Design (10-12 pages)      │
│ Problem statement, context │ LLM code gen, RAG, agentic  │ LangGraph state machine,    │
│ exhaustion, hypothesis     │ decomposition, Goodhart's   │ AST chunking, Dual-Contract │
├────────────────────────────┼─────────────────────────────┼─────────────────────────────┤
│ Chapter 4: Implementation  │ Chapter 5: Empirical        │ Chapter 6: Threats, Ethics  │
│ Details (10-14 pages)      │ Evaluation (10-12 pages)    │ & Conclusion (6-8 pages)    │
│ Agents, tools, sandbox, RAG│ Day 5 experiments, LaTeX    │ Threats to validity, AI     │
│ cascade, guardrails        │ tables, plots, error analysis│ ethics log, future work     │
└────────────────────────────┴─────────────────────────────┴─────────────────────────────┘
```

* **Chapter 1: Introduction (5–7 pages)**: Sections 1.1 and 1.2 of this document.
* **Chapter 2: Literature Review & Related Work (8–10 pages)**: LLM software engineering, RAG in codebases, cognitive agent decomposition, and Goodhart's Law in automated evaluation.
* **Chapter 3: System Design & Architecture (10–12 pages)**: Section 2 (Days 1–4 architecture), Section 4 (Agent roster and guardrails), Section 3 (Technology matrix).
* **Chapter 4: Implementation & Engineering Resilience (10–14 pages)**: Day 1–4 engineering chronicle, 24 decision logs, AST chunking implementation, model cascade, and sandbox diagnostics.
* **Chapter 5: Empirical Benchmark & Results (10–12 pages)**: Day 5 comparative study (No-RAG vs Dense vs Hybrid), LaTeX tables, performance plots, and Failure Taxonomy.
* **Chapter 6: Discussion, Threats to Validity & Future Work (6–8 pages)**: Limitations identified in "What More Could Have Been Done", single-language constraints, and Policy-RAG roadmaps.

