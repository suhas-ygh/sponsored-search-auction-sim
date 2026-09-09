"""Brand brief -> campaign plan.

Deterministic heuristic for now. The LLM planner (TODO(agent)) should expose
this same function as a tool: {"name": "plan_campaign", "args": brief}.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class CampaignPlan:
    category: str
    objective: str
    budget: float
    target_roas: float
    bids: dict = field(default_factory=dict)  # product_id -> {"bid", "budget"}


def plan_from_brief(brief: dict, catalog: pd.DataFrame, max_products: int = 12) -> CampaignPlan:
    """brief keys: category, budget, objective ("share_growth" | "roas"),
    target_roas (used when objective == "roas")."""
    cat = brief["category"]
    cands = catalog[catalog["category"] == cat].copy()
    if cands.empty:
        raise ValueError(f"No products in category {cat!r}")

    # Weight by expected margin dollars; ROAS objective tilts to converters.
    cands["weight"] = cands["price"] * cands["margin_rate"] * (0.5 + cands["quality"])
    if brief.get("objective") == "roas":
        cands["weight"] *= cands["base_cvr"] / cands["base_cvr"].mean()
    cands = cands.nlargest(max_products, "weight")

    target_roas = float(brief.get("target_roas", 4.0))
    total_w = float(cands["weight"].sum())
    bids: dict = {}
    for _, r in cands.iterrows():
        share = float(r["weight"]) / total_w
        value_per_click = float(r["price"] * r["margin_rate"] * r["base_cvr"])
        bid = round(max(0.10, value_per_click / target_roas * 1.2), 2)
        bids[r["product_id"]] = {"bid": bid, "budget": round(float(brief["budget"]) * share, 2)}
    return CampaignPlan(
        category=cat,
        objective=brief.get("objective", "share_growth"),
        budget=float(brief["budget"]),
        target_roas=target_roas,
        bids=bids,
    )

# Agent wiring: see llm/planner.py — plan_from_text() parses a free-text brief
# and calls plan_from_brief as the `plan_campaign` tool inside a small
# provider-agnostic tool loop. The heuristic stays the system of record.
