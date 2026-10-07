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
