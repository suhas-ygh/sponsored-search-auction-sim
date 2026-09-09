"""Post-flight analysis: deterministic insights now, LLM narration later."""
from __future__ import annotations

import pandas as pd


def post_flight_analysis(summary: dict, results: pd.DataFrame) -> str:
    won = results[results["winner_id"].notna()]
    if not won.empty:
        per_product = (
            won.groupby("winner_id")
            .agg(spend=("price_paid", "sum"),
                 revenue=("attributed_revenue", "sum"),
                 clicks=("clicked", "sum"))
            .reset_index()
        )
        per_product["roas"] = per_product["revenue"] / per_product["spend"].replace(0, float("nan"))
        top = per_product.sort_values("revenue", ascending=False).head(3)

        def _roas(r) -> str:
            return f"{r.roas:.2f}" if pd.notna(r.roas) else "n/a"

        top_lines = "\n".join(
            f"- {r.winner_id}: ${r.spend:.2f} spend → ${r.revenue:.2f} revenue (ROAS {_roas(r)})"
            for r in top.itertuples()
        )
    else:
        top_lines = "- No winning impressions."

    lines = [
        "# Post-flight analysis",
        f"- Spend ${summary['spend']:.2f} → ${summary['attributed_revenue']:.2f} "
        f"attributed revenue (ROAS {summary['roas']:.2f})",
        f"- {summary['impressions']} impressions · CTR {summary['ctr']:.2%} · "
        f"CVR {summary['cvr']:.2%} · avg CPC ${summary['avg_cpc']:.2f}",
        "## Top products by attributed revenue",
        top_lines,
        "## Recommendations",
    ]
    if summary["roas"] < 2.0:
        lines.append("- ROAS is soft: cut bids on low-converting SKUs or narrow to high-quality products.")
    if summary["ctr"] < 0.03:
        lines.append("- CTR is low: relevance is the lever — revisit the query→product mapping.")
    if summary["spend"] == 0:
        lines.append("- No spend: bids are below the reserve or budgets are exhausted immediately.")
    # Agent wiring: see llm/narrator.py — narrate_post_flight() turns these
    # bullets into a client-ready recap via LLM, falling back to this text.
    return "\n".join(lines)
