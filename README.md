# Sponsored Search Auction Simulator

An open-source simulator for **sponsored product search auctions** — the engine
behind retail media networks. Point it at a brand brief, and it plans a
campaign, runs thousands of synthetic auctions, paces budget, optimizes bids
toward a ROAS target, and writes a post-flight analysis.

> Independent demo project. All data is synthetic. Not affiliated with Walmart
> or any retailer.

## Quickstart

```bash
pip install -e ".[dev]"

# Run a campaign: $500 budget, oat milk category, ROAS-targeted bidding
python scripts/run_simulation.py --n-auctions 20000 --budget 500 \
    --category "oat milk" --objective roas --target-roas 4.0

# Dashboard
streamlit run app/streamlit_app.py

# Tests + optimizer evals
pytest -q
```

## How it works

1. **Catalog** (`catalog.py`) — generates a synthetic product catalog (price,
   margin, quality/relevance, CTR, CVR) plus a query plan with search volumes.
2. **Brief → plan** (`briefs.py`) — turns a brand brief
   (`category`, `budget`, `objective`, `target_roas`) into per-product bids and
   budgets, anchored on expected profit per click.
3. **Auction** (`auction.py`) — per query, eligible bidders are ranked by
   `bid × quality`; the winner pays second-price
   (`runner_up_ad_rank / winner_quality`), GSP-style, with a reserve price.
   Clicks and conversions are sampled from the product's CTR/CVR.
4. **Pacing** (`pacing.py`) — scales bids so spend lands smoothly across the flight.
5. **Bid optimization** (`bidders.py`) — `TargetRoasBidder` nudges its bid
   multiplier toward the ROAS target after every batch of auctions.
6. **Analysis** (`metrics.py`, `analysis.py`) — ROAS, CTR/CVR/CPC, a
   cannibalization proxy, and a markdown post-flight recap.

## LLM features (`src/auction_sim/llm/`)

Provider-agnostic and dependency-free (stdlib only). Set one of these:

```bash
export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY
# optional: ANTHROPIC_MODEL, OPENAI_MODEL, OPENAI_BASE_URL (for gateways)
```

- **Brief planner** — free text in, campaign plan + rationale out. The model
  may only build plans by calling the deterministic `plan_campaign` tool
  (the heuristic stays the system of record); its job is interpretation and
  explanation.
- **Narrator** — turns the bullet analysis into a client-ready recap, with
  automatic fallback to the deterministic bullets when no key is set.
- **Tool loop** — tiny JSON-protocol agent loop (`{"call": ...}` /
  `{"answer": ...}`), no provider function-calling needed. Malformed output
  and tool errors are fed back for self-correction; every step is recorded
  for tracing.

```bash
# Free-text brief (needs API key)
python scripts/run_simulation.py --brief-text "grow share in oat milk with $800, keep ROAS above 3" --narrate

# Structured brief (no key needed)
python scripts/run_simulation.py --brief-json '{"category":"pasta","budget":300,"objective":"roas"}'
```

Tests use a scripted `FakeLLMClient`, so the whole suite runs offline.

## Project structure

```
src/auction_sim/   library: catalog, auction, pacing, bidders, metrics, briefs, analysis, simulate
scripts/           run_simulation.py (CLI), generate_data.py
app/               streamlit_app.py (dashboard)
evals/             optimizer behavior evals
tests/             unit tests for auction mechanics
```

## Roadmap

- `TODO(agent)` markers: wire an LLM brief planner and a narrative post-flight
  writer as explicit tools.
- Multi-slot auctions, position bias, dayparting.
- Offsite / display extension (reach + frequency).
- Headless eval harness comparing bidder strategies across seeds.
