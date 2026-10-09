# Day 4 Implementation Plan: Hybrid RAG Integration into Agents & Workflow

## 1. Executive Summary & Objective
* **Goal**: Seamlessly connect the standalone RAG engine built on Day 3 (`app/rag/`) directly into the **Planner** and **Coder** agents within the LangGraph orchestration framework, controlled via a `--rag` toggle switch.
* **Core Hypothesis**: Syntax-aware code retrieval provides targeted function/class context to agents, significantly reducing hallucinations, cutting token consumption, and improving test-passing patch success on multi-file repositories.
* **Done When**:
  - `python -m app.main --repo <path> --task <task> --rag` successfully retrieves context and drives the agent pipeline.
  - Baseline execution without `--rag` remains 100% backward-compatible and unaffected.
  - All unit and integration tests pass offline (`pytest -q`).
  - `evaluation/run_eval.py` supports `--rag` and `--rag-mode` for comparative benchmarks.

---

## 2. Architecture & Data Flow

```
                      User Task & Target Repository
                                   │
                                   ▼
                 [app/main.py]  /  [evaluation/run_eval.py]
                                   │
                                   ▼
                 [app/graph.py] run_task(task, repo, rag=True)
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
   [rag=False (Baseline)]                              [rag=True (RAG Active)]
   - List raw file paths only                          - Query RAG Engine:
   - Planner guesses affected files                      hybrid(task, k=5, repo)
   - Coder reads full raw files                        - Extract top AST chunks
         │                                                   │
         ▼                                                   ▼
   [Planner Agent]                                     [Planner Agent]
   - Prompt: Task + file list                          - Prompt: Task + file list
         │                                               + Matched code symbols/docstrings
         ▼                                                   │
   [Coder Agent]                                             ▼
   - Raw file dumps (up to 12k chars)                  [Coder Agent]
         │                                             - Target AST chunks with parent
         │                                               class & signature context
         │                                             - Budgeted token packing (4k tokens)
         │                                                   │
         └─────────────────────────┬─────────────────────────┘
                                   │
                                   ▼
                            [Run Tests Node]
                       (Syntax check + Sandbox)
                                   │
                                   ▼
                           [Reviewer Agent]
```

---

## 3. Module Breakdown & Deliverables

### Step 1: Shared State Schema (`app/state.py`)
Add typed RAG configuration fields to `State`:
```python
class State(TypedDict, total=False):
    ...
    rag_enabled: bool        # True when --rag is passed
    rag_mode: str           # "hybrid" | "dense" | "bm25"
    retrieved_chunks: list   # Top-k AST code chunks attached to the run
```

### Step 2: Context Retrieval in Planner (`app/agents/planner.py`)
- When `state.get("rag_enabled")`:
  - Execute `hybrid(state["task"], k=5, repo_path=state["repo_path"])` (or specified `rag_mode`).
  - Prepend matched symbols, kinds, and docstrings under a `RELEVANT REPO SYMBOLS:` section in the user prompt.
  - Store the retrieved chunks in `state["retrieved_chunks"]` so downstream nodes (Coder) can reuse them without re-querying.

### Step 3: Budget-Aware Context in Coder (`app/agents/coder.py`)
- When `state.get("rag_enabled")` and `state.get("retrieved_chunks")`:
  - Format retrieved chunks cleanly with file paths and line numbers:
    ```text
    === RETRIEVED RELEVANT CODE (RAG) ===
    [geometry.py::Rectangle.area] (lines 14-18, ~42 tokens)
    class Rectangle:
        def area(self) -> float: ...
    ```
  - Enforce a strict token context budget (e.g. up to 4,000 tokens) using the `token_estimate` metadata computed during chunking.
  - Supplement with relevant test files so the Coder knows what tests expect.

### Step 4: CLI & Workflow Orchestration (`app/main.py` & `app/graph.py`)
- Update `run_task()` in `app/graph.py` to accept `rag: bool = False` and `rag_mode: str = "hybrid"`.
- Update `app/main.py` CLI:
  - Add `--rag` flag (action="store_true").
  - Add `--rag-mode` flag (`choices=["hybrid", "dense", "bm25"]`, default `"hybrid"`).
  - Print RAG status and retrieved chunk count in the execution summary.

### Step 5: Evaluation Harness Integration (`evaluation/run_eval.py`)
- Support `--rag` and `--rag-mode` in `evaluation/run_eval.py`.
- Record whether RAG was enabled in `evaluation/results/eval_results.json` and generated Markdown/LaTeX tables.

### Step 6: Testing & Quality Assurance (`tests/test_agents.py` & `tests/test_rag_integration.py`)
- Unit test planner with RAG enabled using `FakeEmbedder` to ensure deterministic, zero-network execution.
- Unit test coder context builder with RAG enabled.
- End-to-end dry-run test verifying the LangGraph state machine completes with `rag_enabled=True`.
- Verify `pytest -q` passes 100% offline.

---

## 4. Done-When Criteria
- [ ] `State` contains `rag_enabled`, `rag_mode`, and `retrieved_chunks`.
- [ ] Planner and Coder prompts dynamically format RAG context when active.
- [ ] `main.py` exposes `--rag` and `--rag-mode`.
- [ ] `evaluation/run_eval.py` accepts `--rag` and logs retrieval usage.
- [ ] All unit tests pass offline with `pytest -q`.
- [ ] Changes committed cleanly to `feature/day4-rag-integration`.

