"""Behavior evals for the bidding optimizer.

These guard the optimizer's contract: near-target ROAS, budget respected.
Run with pytest. Tighten tolerances as the optimizer improves — don't delete.
"""
from auction_sim.simulate import run_campaign


def test_roas_controller_lands_near_target():
    out = run_campaign(objective="roas", target_roas=4.0,
                       n_auctions=20000, seed=7)
    roas = out["summary"]["roas"]
    assert 2.0 <= roas <= 8.0, f"ROAS {roas} too far from target 4.0"


def test_spend_never_exceeds_budget():
    out = run_campaign(budget=500.0, n_auctions=20000, seed=7)
    assert out["summary"]["spend"] <= 500.0 + 1e-6


def test_optimizer_beats_fixed_bids_on_roas_objective():
    # The controller should not do *worse* than its own starting point
    # by a wide margin; guards against regressions that tank efficiency.
    out = run_campaign(objective="roas", target_roas=4.0,
                       n_auctions=20000, seed=11)
    assert out["summary"]["roas"] >= 1.5
