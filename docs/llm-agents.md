# LLM agents

The LLM layer (`src/auction_sim/llm/`) is provider-agnostic and dependency-free
(stdlib `urllib` only). Everything runs offline except the two features below,
which need an API key.

## Setup

```bash
export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY
# optional overrides:
#   ANTHROPIC_MODEL, OPENAI_MODEL, OPENAI_BASE_URL (OpenAI-compatible gateways)
```

With no key set, the planner raises a helpful error and the narrator falls back
to the deterministic bullet analysis — the pipeline never breaks for lack of a key.

## Tool loop

`tools.py` implements a minimal agent loop that needs no provider
function-calling API. The model speaks a tiny JSON protocol — one object per
turn:

```json
{"call": {"tool": "plan_campaign", "arguments": {"category": "oat milk", "budget": 800}}}
{"answer": "Rationale: ..."}
```

Malformed output, unknown tools, and tool errors are fed back into the
conversation so the model can self-correct. Every step is recorded
(`LoopResult.steps`) for tracing. New agent capabilities become `Tool`s:
a name, a description, a JSON-schema-ish parameter spec, and a Python function.

## Brief planner

`planner.plan_from_text(brief_text, catalog, client)` turns free text like
*"grow share in oat milk with $800, keep ROAS above 3"* into a `CampaignPlan`
plus a rationale. Design rule: **the deterministic heuristic is the system of
record** — the model may only produce a plan by calling the `plan_campaign`
tool (which wraps `briefs.plan_from_brief`). Its job is interpretation
(free text → structured brief) and explanation. A `catalog_stats` tool lets it
resolve ambiguous categories before planning.

## Narrator

`narrator.narrate_post_flight(...)` rewrites the deterministic post-flight
bullets as a client-ready recap (headline takeaway, drivers, next steps),
instructed to use only the numbers it's given. Any failure — no key, network
error, empty reply — returns the deterministic text instead.

## Testing without a key

`FakeLLMClient` replays scripted replies, so `tests/test_llm.py` and
`evals/test_planner.py` run offline. They cover the happy path, recovery from
a bad category, malformed-JSON resilience, loop timeouts, and narrator
fallback.
