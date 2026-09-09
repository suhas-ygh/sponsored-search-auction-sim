"""Unit tests for the LLM layer (all offline, via FakeLLMClient)."""
import json

import pytest

from auction_sim.catalog import CATEGORIES, generate_catalog
from auction_sim.llm.client import FakeLLMClient, get_client
from auction_sim.llm.narrator import narrate_post_flight
from auction_sim.llm.planner import plan_from_text
from auction_sim.llm.tools import Tool, run_tool_loop


@pytest.fixture
def catalog():
    return generate_catalog(n_products=120, seed=3)


def _call(tool, **args):
    return json.dumps({"call": {"tool": tool, "arguments": args}})


def test_planner_builds_plan_through_tool(catalog):
    client = FakeLLMClient([
        _call("plan_campaign", category="oat milk", budget=800,
              objective="roas", target_roas=3.0),
        json.dumps({"answer": "Focused budget on high-margin oat milk SKUs; "
                              "bids anchored to profit-per-click at 3x ROAS."}),
    ])
    res = plan_from_text("grow share in oat milk with $800, keep ROAS above 3",
                         catalog, client)
    assert res.plan.category == "oat milk"
    assert res.plan.budget == 800
    assert res.plan.objective == "roas"
    assert 0 < len(res.plan.bids) <= 12
    assert "oat milk" in res.rationale or "ROAS" in res.rationale
    assert any(c["tool"] == "plan_campaign" for c in res.loop.tool_calls)


def test_planner_recovers_from_bad_category(catalog):
    client = FakeLLMClient([
        _call("plan_campaign", category="oatmilk drink", budget=500),
        _call("plan_campaign", category="oat milk", budget=500),
        json.dumps({"answer": "Corrected the category and built the plan."}),
    ])
    res = plan_from_text("oatmilk drink promo, $500", catalog, client)
    assert res.plan.category == "oat milk"
    calls = [c for c in res.loop.tool_calls if c["tool"] == "plan_campaign"]
    assert "error" in calls[0]["result"]  # first attempt failed loudly
    assert "error" not in calls[1]["result"]


def test_tool_loop_survives_malformed_json():
    tools = [Tool("echo", "Echo back.", {"type": "object", "properties": {}},
                  lambda: {"ok": True})]
    client = FakeLLMClient(["not json at all", json.dumps({"answer": "done"})])
    out = run_tool_loop(client, tools, "sys", "hi", max_steps=4)
    assert out.answer == "done"
    assert len(out.steps) >= 2


def test_tool_loop_raises_when_never_finishes():
    tools = [Tool("echo", "Echo back.", {"type": "object", "properties": {}},
                  lambda: {"ok": True})]
    client = FakeLLMClient(["garbage", "more garbage", "still garbage"])
    with pytest.raises(RuntimeError):
        run_tool_loop(client, tools, "sys", "hi", max_steps=2)


def test_narrator_falls_back_without_llm():
    class BrokenClient:
        def complete(self, *a, **k):
            raise RuntimeError("no network")

    md, used_llm = narrate_post_flight(
        summary={"spend": 10.0, "attributed_revenue": 40.0, "roas": 4.0,
                 "eligible_auctions": 100, "clicks": 5, "ctr": 0.05,
                 "conversions": 1, "cvr": 0.2, "avg_cpc": 2.0},
        cannibalization={"incremental_revenue": 30.0,
                         "organic_overlap_rate": 0.25},
        top_products=[{"product_id": "P0001", "spend": 10.0,
                       "revenue": 40.0, "roas": 4.0}],
        fallback_md="## fallback bullets",
        client=BrokenClient(),
    )
    assert used_llm is False
    assert md == "## fallback bullets"


def test_get_client_errors_helpfully_without_keys(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_client()


def test_plan_categories_match_catalog(catalog):
    assert set(catalog["category"].unique()) <= set(CATEGORIES)
