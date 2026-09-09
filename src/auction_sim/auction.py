"""Core auction mechanics: relevance-weighted ranking with GSP-style pricing.

`products` is a DataFrame indexed by product_id (see catalog.generate_catalog).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

RESERVE_PRICE = 0.05  # minimum CPC


@dataclass
class Bidder:
    product_id: str
    bid: float            # base max CPC
    budget: float         # flight budget for this product
    spent: float = 0.0
    revenue: float = 0.0  # attributed sales
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0

    @property
    def remaining(self) -> float:
        return max(self.budget - self.spent, 0.0)

    def effective_bid(self) -> float:
        return self.bid


@dataclass
class AuctionResult:
    query: str
    winner_id: str | None
    price_paid: float
    clicked: bool
    converted: bool
    attributed_revenue: float


def run_auction(
    query: str,
    bidders: list[Bidder],
    products: pd.DataFrame,
    rng: np.random.Generator,
) -> AuctionResult:
    eligible = [
        b for b in bidders
        if b.remaining > RESERVE_PRICE and b.effective_bid() >= RESERVE_PRICE
    ]
    if not eligible:
        return AuctionResult(query, None, 0.0, False, False, 0.0)

    quality = products["quality"]
    ranked = sorted(
        eligible,
        key=lambda b: b.effective_bid() * float(quality.loc[b.product_id]),
        reverse=True,
    )
    winner = ranked[0]
    q_w = float(quality.loc[winner.product_id])

    if len(ranked) > 1:
        runner = ranked[1]
        price = (runner.effective_bid() * float(quality.loc[runner.product_id])) / q_w + 0.01
    else:
        price = RESERVE_PRICE
    price = float(min(winner.effective_bid(), max(price, RESERVE_PRICE)))
    if winner.remaining < price:
        return AuctionResult(query, None, 0.0, False, False, 0.0)

    row = products.loc[winner.product_id]
    p_click = float(np.clip(row["base_ctr"] * (0.5 + q_w), 0.0, 1.0))
    clicked = bool(rng.random() < p_click)
    converted = False
    revenue = 0.0
    winner.impressions += 1
    if clicked:
        winner.clicks += 1
        winner.spent += price
        converted = bool(rng.random() < float(row["base_cvr"]))
        if converted:
            winner.conversions += 1
            revenue = float(row["price"])
            winner.revenue += revenue
    return AuctionResult(query, winner.product_id, price if clicked else 0.0,
                         clicked, converted, revenue)
