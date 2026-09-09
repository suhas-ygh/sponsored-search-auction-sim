"""Campaign metrics: ROAS, profit, and a cannibalization proxy."""
from __future__ import annotations

import pandas as pd


def summarize(results: pd.DataFrame) -> dict:
    eligible = results[results["eligible"]] if "eligible" in results.columns else results
    clicks = int(eligible["clicked"].sum())
    spend = float(eligible["price_paid"].sum())
    revenue = float(eligible["attributed_revenue"].sum())
    impr = len(eligible)
    conv = int(eligible["converted"].sum())
    return {
        "auctions": len(results),
        "eligible_auctions": impr,
        "impressions": impr,
        "clicks": clicks,
        "conversions": conv,
        "spend": round(spend, 2),
        "attributed_revenue": round(revenue, 2),
        "roas": round(revenue / spend, 3) if spend else 0.0,
        "ctr": round(clicks / impr, 4) if impr else 0.0,
        "cvr": round(conv / clicks, 4) if clicks else 0.0,
        "avg_cpc": round(spend / clicks, 3) if clicks else 0.0,
    }


def cannibalization_estimate(summary: dict, organic_overlap: float = 0.25) -> dict:
    """Rough proxy: share of attributed revenue that would have happened
    organically anyway (shopper was already going to buy)."""
    cannibalized = summary["attributed_revenue"] * organic_overlap
    return {
        "organic_overlap_rate": organic_overlap,
        "cannibalized_revenue": round(cannibalized, 2),
        "incremental_revenue": round(summary["attributed_revenue"] - cannibalized, 2),
    }
