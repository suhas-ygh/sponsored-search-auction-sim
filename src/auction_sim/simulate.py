"""Shared campaign runner used by the CLI and the Streamlit app."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .analysis import post_flight_analysis
from .auction import run_auction
from .bidders import TargetRoasBidder
from .briefs import CampaignPlan, plan_from_brief
from .catalog import generate_catalog, query_plan
from .metrics import cannibalization_estimate, summarize
from .pacing import even_pace_multiplier


def run_campaign(
    category: str = "oat milk",
    budget: float = 500.0,
    objective: str = "share_growth",
    target_roas: float = 4.0,
    n_auctions: int = 20000,
    seed: int = 7,
    batch: int = 500,
    plan: CampaignPlan | None = None,
) -> dict:
    rng = np.random.default_rng(seed)
    catalog = generate_catalog(seed=seed)
    products = catalog.set_index("product_id")
    cat_of = products["category"].to_dict()

    if plan is None:
        plan = plan_from_brief(
            {"category": category, "budget": budget,
             "objective": objective, "target_roas": target_roas},
            catalog,
        )
    bidders = [
        TargetRoasBidder(pid, cfg["bid"], cfg["budget"], target_roas=plan.target_roas)
        for pid, cfg in plan.bids.items()
    ]

    queries = query_plan(catalog, seed=seed)
    q_list = queries["query"].tolist()
    q_cat = queries.set_index("query")["category"].to_dict()
    probs = queries["volume"].to_numpy()

    rows: list[dict] = []
    snapshots = {b.product_id: (b.spent, b.revenue) for b in bidders}
    for i in range(1, n_auctions + 1):
        q = q_list[int(rng.choice(len(q_list), p=probs))]
        cands = [b for b in bidders if cat_of[b.product_id] == q_cat[q]]
        for b in cands:
            b.pace_mult = even_pace_multiplier(b.spent, b.budget, i, n_auctions)
        res = run_auction(q, cands, products, rng)
        rows.append({"query": q, "eligible": len(cands) > 0, **res.__dict__})
        if i % batch == 0:
            for b in bidders:
                s0, r0 = snapshots[b.product_id]
                b.observe(b.spent - s0, b.revenue - r0)
                b.update()
                snapshots[b.product_id] = (b.spent, b.revenue)

    results = pd.DataFrame(rows)
    summary = summarize(results)
    won = results[results["winner_id"].notna()]
    if not won.empty:
        tbl = (won.groupby("winner_id")
               .agg(spend=("price_paid", "sum"),
                    revenue=("attributed_revenue", "sum"))
               .reset_index())
        tbl["roas"] = (tbl["revenue"] / tbl["spend"]).round(2)
        top_products = [
            {"product_id": r.winner_id, "spend": round(float(r.spend), 2),
             "revenue": round(float(r.revenue), 2),
             "roas": float(r.roas) if pd.notna(r.roas) else 0.0}
            for r in tbl.sort_values("revenue", ascending=False).head(5).itertuples()
        ]
    else:
        top_products = []
    return {
        "summary": summary,
        "cannibalization": cannibalization_estimate(summary),
        "results": results,
        "catalog": catalog,
        "plan": plan,
        "bidders": bidders,
        "top_products": top_products,
        "analysis_md": post_flight_analysis(summary, results),
    }
