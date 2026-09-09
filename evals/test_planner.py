"""Planner behavior evals: varied brief phrasings must all yield valid plans.

Scripted (FakeLLMClient) so they run offline; they guard the planner's
contract, not any particular model's wording.
"""
import json

from auction_sim.catalog import generate_catalog
from auction_sim.llm.client import FakeLLMClient
from auction_sim.llm.planner import plan_from_text


def _run(brief_text, tool_args):
    catalog = generate_catalog(n_products=120, seed=3)
    replies = [
        json.dumps({"call": {"tool": "plan_campaign", "arguments": tool_args}}),
        json.dumps({"answer": "Rationale."}),
    ]
    res = plan_from_text(brief_text, catalog, FakeLLMClient(replies))
    assert res.plan.category in catalog["category"].unique()
    assert res.plan.budget == tool_args["budget"]
    assert len(res.plan.bids) > 0
    assert res.rationale.strip()
    return res


def test_brief_with_roas_constraint():
    _run("grow share in oat milk with $800, keep ROAS above 3",
         {"category": "oat milk", "budget": 800,
          "objective": "roas", "target_roas": 3.0})


def test_terse_brief_defaults_objective():
    _run("pasta $250",
         {"category": "pasta", "budget": 250})


def test_brief_naming_category_indirectly():
    _run("$1200 for the yogurt line, efficiency first, target 5x",
         {"category": "greek yogurt", "budget": 1200,
          "objective": "roas", "target_roas": 5.0})
