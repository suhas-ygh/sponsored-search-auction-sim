"""Unit tests for auction mechanics."""
import numpy as np
import pandas as pd

from auction_sim.auction import RESERVE_PRICE, Bidder, run_auction
from auction_sim.catalog import generate_catalog


def _products(seed: int = 0) -> pd.DataFrame:
    return generate_catalog(n_products=20, seed=seed).set_index("product_id")


def test_winner_is_highest_ad_rank():
    products = _products()
    products["quality"] = 0.5  # isolate bid effect
    pids = products.index.tolist()[:3]
    bidders = [Bidder(pid, bid=b, budget=100.0) for pid, b in zip(pids, [1.0, 2.0, 3.0])]
    rng = np.random.default_rng(0)
    res = run_auction("oat milk", bidders, products, rng)
    assert res.winner_id == pids[2]


def test_price_never_exceeds_winning_bid():
    products = _products()
    rng = np.random.default_rng(1)
    for _ in range(200):
        pids = rng.choice(products.index.tolist(), size=4, replace=False)
        bidders = [Bidder(pid, bid=float(rng.uniform(0.1, 3.0)), budget=100.0)
                   for pid in pids]
        res = run_auction("granola", bidders, products, rng)
        if res.winner_id is not None:
            winner_bid = next(b.bid for b in bidders if b.product_id == res.winner_id)
            assert res.price_paid <= winner_bid + 1e-9
            assert res.price_paid >= RESERVE_PRICE - 1e-9 or not res.clicked


def test_budget_is_respected():
    products = _products()
    pid = products.index[0]
    b = Bidder(pid, bid=5.0, budget=10.0)
    rng = np.random.default_rng(2)
    for _ in range(5000):
        run_auction("pasta", [b], products, rng)
    assert b.spent <= b.budget + 1e-9


def test_reserve_price_filters_dust_bids():
    products = _products()
    pid = products.index[0]
    b = Bidder(pid, bid=0.01, budget=100.0)
    rng = np.random.default_rng(3)
    res = run_auction("salsa", [b], products, rng)
    assert res.winner_id is None


def test_no_bidders_no_winner():
    products = _products()
    rng = np.random.default_rng(4)
    res = run_auction("salsa", [], products, rng)
    assert res.winner_id is None
    assert res.price_paid == 0.0
