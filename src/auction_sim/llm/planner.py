"""Free-text brand brief -> CampaignPlan, via the tool loop.

The deterministic heuristic (briefs.plan_from_brief) stays the system of
record: the model may only produce a plan by calling it as the `plan_campaign`
tool. The model's job is interpretation (free text -> structured brief) and
explanation (the rationale).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

from ..briefs import CampaignPlan, plan_from_brief
from .tools import LoopResult, Tool, run_tool_loop

PLANNER_SYSTEM = """\
You are a retail media campaign planner. A brand gives you a free-text brief;
you turn it into a concrete sponsored-search campaign.

Rules:
1. If the product category in the brief is ambiguous or you are unsure it \
exists, call catalog_stats first and pick the closest matching category.
2. Call plan_campaign EXACTLY ONCE with the complete brief:
   - category: must be one of the catalog categories, verbatim
   - budget: total flight budget as a number (no currency symbols)
   - objective: "share_growth" (default, maximize reach/conversions) or \
"roas" (efficiency-first)
   - target_roas: number, default 4.0 (matters most when objective is "roas")
3. After the tool returns the plan, finish with {"answer": ...} containing a \
short rationale (3-6 sentences): which products got the most budget and why, \
the bid logic, the key trade-off, and what to watch mid-flight. Ground every \
number in the tool result — never invent figures."""


@dataclass
class PlannerResult:
    plan: CampaignPlan
    rationale: str
    loop: LoopResult = field(default_factory=LoopResult)


def plan_from_text(brief_text: str, catalog: pd.DataFrame, client: Any,
                   max_products: int = 12) -> PlannerResult:
    """Parse a free-text brief and build a CampaignPlan through the tool loop."""

    def catalog_stats() -> dict:
        g = catalog.groupby("category").agg(
            n=("product_id", "size"), avg_price=("price", "mean"))
        return {"categories": {
            str(cat): {"products": int(row["n"]),
                       "avg_price": round(float(row["avg_price"]), 2)}
            for cat, row in g.iterrows()}}

    def plan_campaign(category: str, budget: float,
                      objective: str = "share_growth",
                      target_roas: float = 4.0) -> dict:
        plan = plan_from_brief(
            {"category": category, "budget": budget,
             "objective": objective, "target_roas": target_roas},
            catalog, max_products=max_products)
        return asdict(plan)

    tools = [
        Tool("catalog_stats",
             "Per-category product counts and average prices. Takes no arguments.",
             {"type": "object", "properties": {}},
             lambda: catalog_stats()),
        Tool("plan_campaign",
             "Build the campaign plan from a structured brief. Call exactly once.",
             {"type": "object",
              "properties": {
                  "category": {"type": "string"},
                  "budget": {"type": "number"},
                  "objective": {"type": "string",
                                "enum": ["share_growth", "roas"]},
                  "target_roas": {"type": "number"}},
              "required": ["category", "budget"]},
             plan_campaign),
    ]

    loop = run_tool_loop(client, tools, PLANNER_SYSTEM,
                         f"Brand brief: {brief_text}")
    good = [c for c in loop.tool_calls
            if c["tool"] == "plan_campaign" and "error" not in c["result"]]
    if not good:
        raise RuntimeError("Planner finished without producing a campaign plan.")
    d = good[-1]["result"]
    plan = CampaignPlan(category=d["category"], objective=d["objective"],
                        budget=float(d["budget"]),
                        target_roas=float(d["target_roas"]), bids=d["bids"])
    return PlannerResult(plan=plan, rationale=loop.answer, loop=loop)
