"""Budget pacing: scale bids so spend lands smoothly across the flight."""
from __future__ import annotations


def even_pace_multiplier(spent: float, budget: float,
                         auctions_done: int, auctions_total: int) -> float:
    """Return a bid multiplier in [0.2, 2.0].

    Behind pace (spent < pro-rata expectation) -> bid up; ahead -> bid down.
    """
    if auctions_total <= 0 or budget <= 0:
        return 1.0
    expected_spend = budget * (auctions_done / auctions_total)
    if expected_spend <= 0:
        return 1.0
    ratio = spent / expected_spend
    mult = 1.0 + (1.0 - ratio) * 0.5
    return float(min(2.0, max(0.2, mult)))
