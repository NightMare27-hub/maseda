# Decision log
| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-10-07 | Resilient JSON parser in `app/llm.py` | Models frequently prepend commentary or include trailing commas; regex code-block extraction prevents unnecessary retry calls. | Rely only on raw `json.loads` or re-querying LLM. |
| 2026-10-07 | Cumulative metrics tracking in `State` and CLI summary | Prepares for Day 2 baseline evaluation by tracking tokens, cost, and latency across iterations. | Only logging to disk in JSONL without CLI summary. |
| 2026-10-07 | Explicit `PYTHONPATH` and exit code 5 diagnostic in sandbox | Prevents module import resolution issues and provides clear feedback when 0 tests are collected. | Leaving standard subprocess environment. |
| 2026-10-08 | Dedicated `Reviewer` agent in LangGraph | Test exit codes lack semantic reasoning. Reviewer generates structured diagnosis and targeted fixes for Coder, and verifies solutions satisfy task requirements. | Passing raw test output back without LLM critique. |
| 2026-10-08 | Multi-module `bench_repo` and 20-task benchmark | Enables rigorous evaluation of bug fixes, features, edge cases, and cross-module dependencies needed to test RAG impact. | Using only single-file toy repo. |
| 2026-10-08 | AST Syntax pre-validation before sandbox | Catch syntax errors via `ast.parse` immediately with precise line/column feedback instead of waiting for subprocess test runs. | Relying exclusively on subprocess pytest failures. |
| 2026-10-08 | Oscillation & Repeat-Edit Circuit Breaker | Detects identical repeated edits, injects warnings, and halts after 2 stagnated rounds to avoid token burn. | Allowing endless loops until max iterations. |
| 2026-10-08 | SWE-bench style failing setup edits & LaTeX report export | Guarantees test verification by ensuring tasks fail pre-patch, and generates thesis-ready LaTeX tables automatically. | Manual report generation and testing on already-green repos. |
