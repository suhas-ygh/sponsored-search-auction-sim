"""Bidder strategies.

`TargetRoasBidder` is a simple controller: after every batch of auctions it
nudges its bid multiplier toward the ROAS target. Swap in bandits / MPC here.
"""
from __future__ import annotations

from dataclasses import dataclass

from .auction import Bidder


@dataclass
class TargetRoasBidder(Bidder):
    target_roas: float = 4.0
    multiplier: float = 1.0   # learned bid adjustment
    pace_mult: float = 1.0    # set by the pacing layer each auction
    _window_spend: float = 0.0
    _window_revenue: float = 0.0

    def effective_bid(self) -> float:
        return self.bid * self.multiplier * self.pace_mult

    def observe(self, spend: float, revenue: float) -> None:
        self._window_spend += spend
        self._window_revenue += revenue

    def update(self, k: float = 0.3) -> None:
        if self._window_spend > 0:
            roas = self._window_revenue / self._window_spend
            self.multiplier *= 1.0 + k * (roas - self.target_roas) / self.target_roas
            self.multiplier = float(min(3.0, max(0.25, self.multiplier)))
        self._window_spend = 0.0
        self._window_revenue = 0.0
