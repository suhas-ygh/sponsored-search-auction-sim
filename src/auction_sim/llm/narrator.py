"""LLM post-flight narrator with deterministic fallback.

narrate_post_flight tries the LLM once; on any failure (no API key, network
error, empty reply) it returns the deterministic bullet analysis so the
pipeline never breaks for lack of a key.
"""
from __future__ import annotations

from typing import Any

from .client import get_client

NARRATOR_SYSTEM = """\
You are a retail media analyst writing a client-ready campaign recap for a
brand manager. You receive campaign numbers and a bullet analysis. Write a
concise markdown recap: headline takeaway, what drove performance, and 2-3
concrete next steps. Use ONLY the numbers provided — never invent or round
them into new claims. Keep it under 250 words, no fluff."""


def narrate_post_flight(*, summary: dict, cannibalization: dict,
                        top_products: list[dict], fallback_md: str,
                        client: Any | None = None) -> tuple[str, bool]:
    """Returns (markdown, used_llm)."""
    if client is None:
        try:
            client = get_client()
        except RuntimeError:
            return fallback_md, False
    top_lines = "\n".join(
        f"- {p['product_id']}: ${p['spend']:.2f} spend, "
        f"${p['revenue']:.2f} revenue, ROAS {p['roas']:.2f}"
        for p in top_products
    ) or "- (none)"
    user = (
        "Campaign results:\n"
        f"- Spend ${summary['spend']:.2f}, attributed revenue "
        f"${summary['attributed_revenue']:.2f}, ROAS {summary['roas']:.2f}\n"
        f"- {summary['eligible_auctions']} eligible auctions, "
        f"{summary['clicks']} clicks (CTR {summary['ctr']:.2%}), "
        f"{summary['conversions']} conversions (CVR {summary['cvr']:.2%}), "
        f"avg CPC ${summary['avg_cpc']:.2f}\n"
        f"- Est. incremental revenue ${cannibalization['incremental_revenue']:.2f} "
        f"(organic overlap {cannibalization['organic_overlap_rate']:.0%})\n"
        f"Top products:\n{top_lines}\n\n"
        f"Analyst notes:\n{fallback_md}"
    )
    try:
        text = client.complete([{"role": "user", "content": user}],
                               system=NARRATOR_SYSTEM, max_tokens=600)
        if not text.strip():
            raise ValueError("empty reply")
        return text, True
    except Exception:  # noqa: BLE001 - fallback is the contract
        return fallback_md, False
