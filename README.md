# Multi-Agent Software Development Assistant

A multi-agent assistant (Planner, Coder, Reviewer) that turns a coding task into a tested patch,
plus an evaluation of whether RAG over the codebase improves results.

## Setup
```bash
git clone <repo-url> && cd maseda
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then add your own API key
```

## Structure
- `app/` agents, tools, RAG, UI
- `evaluation/` task set and experiment scripts
- `docs/` architecture, decision log, AI usage log
- `logs/` run logs (not committed)

## Team workflow
- One branch per feature: `git checkout -b feature/<name>`
- Small commits, open a pull request, merge only working code
- Never commit `.env` or API keys

## Run (Day 1)
```bash
# in .env set MODEL (for example gpt-4o-mini, claude-sonnet-4-5, gemini/gemini-2.0-flash) and the matching API key
pytest -q                                   # offline tests, fake LLM, no key needed
python -m app.main --repo evaluation/toy_repo \
  --task "Implement divide(a, b) in calculator.py. It must raise ValueError with a clear message when b is zero."
```
Add `--apply` to write a successful patch into the repo. Every run is logged to `logs/<run_id>.jsonl`.
The test runner is NOT sandboxed yet (Docker comes on Day 6): only run it on repos you trust.
