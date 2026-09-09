# Contributing

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Ground rules

- **Synthetic data only.** Never add real retailer, brand, or marketplace data.
- **Evals stay green.** Changes to bidding logic must keep `evals/test_optimizer.py`
  passing; planner/narrator changes must keep `evals/test_planner.py` passing.
  Tighten tolerances as behavior improves — don't delete evals.
- **Deterministic core, LLM at the edges.** The auction engine, planner
  heuristic, and metrics are pure and seeded. The LLM interprets and explains,
  and may only act through declared tools (`src/auction_sim/llm/tools.py`).
- **Thin app layer.** The Streamlit dashboard calls `simulate.run_campaign`;
  no business logic in `app/`.
- New bidder strategies subclass `Bidder` in `bidders.py`.
- Tests use the scripted `FakeLLMClient` so the suite runs offline.

## Project conventions

See `.cursorrules` for the full list (layout, commands, and agent wiring notes).
