# AI usage log
| Date | Tool | What for | What we changed or checked |
|---|---|---|---|
| 2026-10-07 | Antigravity | Day 1 hardening & metric instrumentation | Hardened `parse_json` against embedded markdown & trailing commas, instrumented `State` with cumulative token/cost/latency metrics, improved sandbox diagnostics for zero-test repositories, updated `main.py` CLI output, added 3 new unit tests (10 passing). |
| 2026-10-08 | Antigravity | Day 2 Reviewer agent & benchmark harness | Created `Reviewer` agent (`reviewer.py`), integrated into LangGraph state machine, built 20-task benchmark (`tasks.json` + `bench_repo`), implemented automated evaluator (`run_eval.py`), added unit tests (13 passing). |
| 2026-10-08 | Antigravity | Day 2 Advanced Additions (AST, Circuit Breaker, SWE-bench scaffolding, LaTeX exporter) | Added AST syntax pre-check, stagnation circuit breaker in coder, SWE-bench style initial failing states for all 20 tasks, `--mock` dry-run mode, and automatic dissertation LaTeX table exporter. All 15 unit tests passing. |
| 2026-10-09 | Codex | Day 3 standalone RAG pipeline | Restored eval baseline, created `feature/day3-rag-ingestion`, added AST chunking, injectable embeddings, Chroma ingest, dense/BM25/hybrid retrieval, offline RAG tests, and slow recall@5 benchmark. |
| 2026-10-09 | Antigravity | Day 3 Enhancements (AST Syntax fallback & IR metrics) | Added `SyntaxError` fallback in `app/rag/chunk.py`, unit test in `test_rag.py`, enhanced slow benchmark with `Recall@1`, `Recall@5`, and `MRR` reporting, aligned `docs/day3_implementation_plan.md`. |
