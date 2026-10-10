# Day 5 Implementation Plan: Comparative Benchmark Experiments & Dissertation Analytics

## 1. Executive Summary & Objective
* **Goal**: Conduct a rigorous, statistically grounded comparative study across the 20-task benchmark evaluating three operational conditions:
  1. **Condition A: Baseline (No-RAG)** – Naive full-file dumps and path guessing without AST retrieval context.
  2. **Condition B: Dense RAG** – Semantic vector retrieval via Chroma embeddings.
  3. **Condition C: Hybrid RAG** – Reciprocal Rank Fusion (RRF) combining BM25 keyword matching and dense semantic search.
* **Core Research Question**: *Does syntax-aware code retrieval (AST-based RAG) improve the functional pass rate, token efficiency, monetary cost, and convergence speed of multi-agent software engineering workflows compared to naive whole-repo dumps?*
* **Target Deliverables**:
  1. **Automated Comparative Experiment Runner** (`evaluation/run_experiments.py`): Orchestrates multi-condition sweeps, trial repetitions, checkpointing, and fail-safe resumption.
  2. **Statistical Aggregation Engine**: Computes descriptive statistics (mean $\mu$, sample standard deviation $\sigma$, confidence intervals, category breakdowns).
  3. **Publication-Ready Dissertation Exporters**:
     - Automated LaTeX tables formatted for thesis submission (`\begin{table}`, `\toprule`, etc.).
     - Comprehensive Markdown comparative report (`evaluation/results/day5_comparative_report.md`).
     - Vector/PNG visualization charts (Pass Rate by Category, Token Consumption Delta, Convergence Rounds).
  4. **Failure Taxonomy & Qualitative Case Analysis**: Categorizes errors into retrieval misses, context dilution, syntax invalidation, and operational/stubbing failures.
  5. **100% Offline Test Suite** (`tests/test_day5_experiments.py`): Validates mock experiment execution, statistical computations, and export formatting without API expenditure or network access.

---

## 2. Experimental Architecture & Workflow

```
                                 [evaluation/tasks.json]
                                  (20 SWE-bench Tasks)
                                            │
                                            ▼
                           [evaluation/run_experiments.py]
                   Orchestrator: Sweeps across experimental conditions
                                            │
         ┌──────────────────────────────────┼──────────────────────────────────┐
         ▼                                  ▼                                  ▼
   Condition A:                       Condition B:                       Condition C:
   Baseline (No-RAG)                  Dense RAG                          Hybrid RAG (RRF)
   --rag=False                        --rag --rag-mode=dense             --rag --rag-mode=hybrid
         │                                  │                                  │
         └──────────────────────────────────┼──────────────────────────────────┘
                                            ▼
                           [Multi-Agent Execution Pipeline]
                       Planner ──► Coder ──► Sandbox ──► Reviewer
                                            │
                                            ▼
                           [Raw Execution Results (JSON)]
                       Pass/Fail, Tokens, Cost, Seconds, Rounds, Chunks
                                            │
                                            ▼
                           [Statistical Aggregator & Analytics]
                       - Mean & Standard Deviation across trials
                       - Category breakdowns (Bugfix, Feature, Edge, Multi-File)
                       - Token Efficiency Index ($E_{tokens} = \frac{\Delta Tokens}{Tokens_{base}}$)
                                            │
         ┌──────────────────────────────────┼──────────────────────────────────┐
         ▼                                  ▼                                  ▼
   [LaTeX Exporter]                  [Markdown Report]                  [Plot Generator]
   Ready-to-paste tables             Comprehensive narrative            High-res charts
   for dissertation chapters         with failure analysis              (Pass rate, tokens, rounds)
```

---

## 3. Detailed Step-by-Step Implementation Breakdown

### Step 1: Branch Creation & Environment Preparation
- Create and switch to a dedicated feature branch:
  ```powershell
  git checkout -b feature/day5-benchmark-experiments
  ```
- **Dependency Policy (Rule 8)**: Add `matplotlib` to `requirements.txt` specifically for generating dissertation figures. Provide an autonomous fallback to vector SVG generation if `matplotlib` is unavailable in minimal environments.

---

### Step 2: Automated Comparative Experiment Runner (`evaluation/run_experiments.py`)
Create a dedicated CLI script that automates multi-condition experimentation:
* **CLI Arguments**:
  - `--conditions`: List of conditions to evaluate (choices: `no-rag`, `dense`, `hybrid`; default: all three).
  - `--trials`: Number of repeated runs per task (default: `1` for full live runs, configurable up to `3` for variance analysis).
  - `--mock`: Fast zero-cost offline validation mode simulating golden executions and stochastic variance.
  - `--tasks`: Path to `evaluation/tasks.json`.
  - `--limit`: Run on a subset of tasks (e.g. `--limit 4` for quick sanity checks).
  - `--category`: Filter by task category (`bugfix`, `feature`, `edge_case`, `multi_file`).
  - `--output-dir`: Output folder for reports, charts, and raw JSON data (`evaluation/results/day5/`).
* **Robustness Features**:
  - **Checkpointing**: Saves intermediate results after every task to allow resuming interrupted runs.
  - **Temp Repo Isolation**: Copies `evaluation/bench_repo` to an isolated temporary directory for every single run, applying `setup_edits` and cleaning up securely.
  - **Live Progress Logging**: Real-time progress meter displaying current task, condition, round, tokens, and pass/fail icon.

---

### Step 3: Statistical Metrics Engine (`evaluation/experiment_analytics.py`)
Implement an analytical engine computing academic evaluation metrics:
* **Core Metrics**:
  1. **Pass Rate ($P_R$)**: Percentage of tasks passing all sandbox unit tests and Reviewer Gate 1 + Gate 2:
     $$P_R = \frac{N_{passed}}{N_{total}} \times 100\%$$
  2. **Token Economy ($\Delta T$)**: Relative reduction in token consumption compared to baseline:
     $$\Delta T = \frac{\bar{T}_{baseline} - \bar{T}_{rag}}{\bar{T}_{baseline}} \times 100\%$$
  3. **Monetary Cost Efficiency**: Cost in USD per successfully resolved task.
  4. **Latency Footprint**: Mean wall-clock time in seconds per task ($\mu \pm \sigma$).
  5. **Convergence Velocity**: Average iteration rounds needed to reach an approved patch ($1.0$ = one-shot pass, $2.0$ = required one reviewer revision).
* **Category Stratification**:
  - Stratifies metrics across `Bugfix` (4 tasks), `Feature` (10 tasks), `Edge_Case` (4 tasks), and `Multi_File` (2 tasks).
  - Special focus on `Multi_File` tasks to quantify the hypothesis that RAG provides the highest value when code spans multiple modules.

---

### Step 4: Publication-Quality Dissertation Exporters
Generate artifacts ready for direct inclusion into the dissertation:

#### A. LaTeX Tables (`day5_tables.tex`)
- Table 1: **Overall Comparative Performance** (Condition, Pass Rate, Mean Rounds, Mean Tokens, Mean Cost, Mean Latency).
- Table 2: **Category-Wise Pass Rate & Efficiency Matrix** (Rows: Categories; Columns: No-RAG vs Dense vs Hybrid).
- Styled using clean academic LaTeX standards (`booktabs`, `tabular`, proper math alignment).

#### B. Markdown Report (`evaluation/results/day5/comparative_report.md`)
- Executive summary with high-level conclusions.
- Full results matrix with side-by-side tables.
- Statistical significance commentary.

#### C. Visual Charts (`evaluation/results/day5/charts/`)
Implement visualization generation using `matplotlib` (with pure SVG fallback):
1. `fig1_pass_rate_by_condition.png`: Grouped bar chart of pass rates across task categories.
2. `fig2_token_consumption.png`: Box plot / bar comparison of total token consumption (Baseline vs Dense vs Hybrid).
3. `fig3_convergence_rounds.png`: Distribution of iteration rounds needed to pass.
4. `fig4_cost_vs_accuracy.png`: Scatter/Pareto trade-off between total cost and final pass rate.

---

### Step 5: Failure Mode Taxonomy & Qualitative Case Study Analyzer
Create an automated failure diagnostic module (`evaluation/failure_analysis.py`):
* Inspects failed tasks and inspects logs to classify causes:
  1. **Type I: Retrieval Miss (Context Omission)** – The required symbol/function was not present in the top-k retrieved chunks.
  2. **Type II: Context Dilution (Noise Overload)** – Irrelevant chunks displaced necessary context within the 3,500 token limit.
  3. **Type III: Syntax Invalidation (AST Failure)** – Model generated invalid Python syntax caught by AST pre-check.
  4. **Type IV: Gate 2 Usability Failure (Hollow Stubbing)** – Unit tests passed but Reviewer rejected hollow or non-operational implementation.
  5. **Type V: Logic Bug (Sandbox Failure)** – Implementation ran but failed behavioral assertions.
* Selects 2 concrete qualitative case studies (1 where RAG won decisively, 1 where RAG failed or matched baseline) for in-depth dissertation prose analysis.

---

### Step 6: Unit & Integration Test Suite (`tests/test_day5_experiments.py`)
Ensure 100% offline test coverage without requiring live API calls:
* `test_experiment_runner_mock_all_conditions()`: Runs all 3 conditions on mock tasks; asserts valid output schema and 100% completion.
* `test_statistical_aggregator_metrics()`: Tests mathematical correctness of pass rate, mean, std dev, and token delta calculations with edge cases (zero division, empty lists).
* `test_latex_exporter_syntax()`: Validates that generated LaTeX strings contain matching `\begin{table}` and `\end{table}`, valid column counts, and properly escaped characters.
* `test_failure_analysis_taxonomy()`: Tests categorization of synthetic failure runs into proper error types.
* Verify `pytest -q` passes completely offline with zero warnings/regressions.

---

## 4. Work Breakdown & Execution Timeline

| Phase | Task | Files Modified / Created | Done-When Criteria |
|:---|:---|:---|:---|
| **Phase 1** | Branch & Dependencies | `requirements.txt`, git branch | Branch created; `matplotlib` added with documented rationale. |
| **Phase 2** | Experiment Orchestrator | `evaluation/run_experiments.py` | Multi-condition CLI supports `--conditions`, `--mock`, `--limit`, and live streaming progress. |
| **Phase 3** | Analytics & LaTeX Exporter | `evaluation/experiment_analytics.py` | Computes statistical metrics and formats academic LaTeX/Markdown tables. |
| **Phase 4** | Visualization Engine | `evaluation/plot_experiments.py` | Generates publication figures (Pass Rate, Tokens, Rounds, Cost). |
| **Phase 5** | Failure Taxonomy Engine | `evaluation/failure_analysis.py` | Classifies failures into Type I–V taxonomy; extracts case studies. |
| **Phase 6** | Unit Tests & Offline Verification | `tests/test_day5_experiments.py` | All new unit tests pass in `pytest -q` completely offline in < 25s. |
| **Phase 7** | Live Experiment Execution | `evaluation/results/day5/` | Live benchmark run executed on target models; reports & charts generated. |
| **Phase 8** | Documentation & Handover | `docs/decisions.md`, `docs/ai_usage_log.md` | Decision logs updated; ready for Day 6 (Streamlit UI & Docker Sandbox). |

---

## 5. Done-When Criteria (Verification Checklist)
- [ ] `git branch` is on `feature/day5-benchmark-experiments`.
- [ ] `evaluation/run_experiments.py` executes No-RAG, Dense, and Hybrid conditions in `--mock` mode in < 5 seconds.
- [ ] LaTeX table exporter outputs compilation-ready tables matching dissertation specifications.
- [ ] Visualization scripts export clear, labeled charts (PNG and SVG) comparing conditions.
- [ ] Failure taxonomy script parses run logs and categorizes failures into structured academic categories.
- [ ] `tests/test_day5_experiments.py` passes 100% offline.
- [ ] Full project test suite passes: `pytest -q` (all existing 37 tests + new Day 5 tests).
- [ ] Documented in `docs/decisions.md` and `docs/ai_usage_log.md`.
