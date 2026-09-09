# Methodology

How the simulator works under the hood, and where it deliberately simplifies.

## Auction mechanics

Each auction is a single-slot, relevance-weighted auction in the style of
sponsored product search:

1. **Eligibility.** Bidders with remaining budget above the reserve price and
   an effective bid at or above it may compete.
2. **Ranking.** Candidates are ranked by *ad rank* = `effective_bid × quality`,
   where `quality` is the product's relevance score in `[0, 1]`.
3. **Pricing.** Generalized second price: the winner pays
   `(runner_up_ad_rank / winner_quality) + $0.01`, capped at their own bid and
   floored at the reserve price (`$0.05`). A sole bidder pays the reserve.
4. **Outcomes.** Clicks are sampled with
   `P(click) = base_ctr × (0.5 + quality)`; conversions with `P(conv) = base_cvr`.
   Attributed revenue is the product's price on conversion; spend accrues only
   on clicks.

Effective bid = `base_bid × roas_multiplier × pace_multiplier`, so the pacing
layer and the bid controller both act through the bid.

## Budget pacing

`pacing.even_pace_multiplier` compares spend against the pro-rata expectation
(`budget × auctions_done / auctions_total`). Behind pace bids up, ahead of pace
bids down, clamped to `[0.2, 2.0]`:

```
multiplier = 1 + (1 − spent / expected_spend) × 0.5
```

## Bid optimization

`TargetRoasBidder` is a proportional controller. After every batch of auctions
(default 500) it observes batch spend and attributed revenue, then nudges its
bid multiplier toward the ROAS target:

```
multiplier *= 1 + k × (roas − target) / target      # k = 0.3
```

clamped to `[0.25, 3.0]`. If ROAS runs hot, bids rise to buy more volume;
if it runs cold, bids fall to restore efficiency. Swap in bandits or MPC in
`bidders.py` — the evals will tell you if they actually help.

## Campaign planning

`briefs.plan_from_brief` turns a structured brief into per-product bids and
budgets. Products are weighted by expected margin dollars
(`price × margin_rate × (0.5 + quality)`); the ROAS objective additionally
tilts toward high converters. Bids anchor on expected profit per click:

```
bid = max($0.10, price × margin_rate × cvr / target_roas × 1.2)
```

Budgets split pro-rata by weight across the top products (default 12).

## Metrics

- **ROAS** = attributed revenue / spend. **CTR** = clicks / eligible auctions,
  **CVR** = conversions / clicks, **avg CPC** = spend / clicks.
- **Cannibalization proxy.** A share of attributed revenue would have happened
  organically. `incremental_revenue = attributed × (1 − organic_overlap)`,
  default overlap 25%. It's a rough, transparent proxy — not a causal estimate.

## Deliberate simplifications

Single ad slot (no position bias), no dayparting, no competitor dynamics
beyond the second-price mechanism, no offsite/display, and fully synthetic
demand. Each is a natural extension — see the README roadmap.
