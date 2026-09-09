"""Streamlit dashboard (thin view over simulate.run_campaign).

Run: streamlit run app/streamlit_app.py
"""
import pandas as pd
import streamlit as st

from auction_sim.catalog import CATEGORIES
from auction_sim.simulate import run_campaign

st.set_page_config(page_title="Auction Simulator", layout="wide")
st.title("Sponsored Search Auction Simulator")
st.caption("Synthetic data only — independent demo, not affiliated with any retailer.")

with st.sidebar:
    category = st.selectbox("Category", CATEGORIES, index=0)
    objective = st.selectbox("Objective", ["share_growth", "roas"])
    budget = st.slider("Campaign budget ($)", 100, 5000, 500, step=50)
    target_roas = st.slider("Target ROAS", 1.0, 10.0, 4.0, step=0.5)
    n_auctions = st.slider("Auctions to simulate", 5_000, 100_000, 20_000, step=5_000)
    seed = st.number_input("Seed", value=7, step=1)
    run = st.button("Run simulation", type="primary")

if run:
    with st.spinner("Running auctions…"):
        out = run_campaign(category=category, budget=budget, objective=objective,
                           target_roas=target_roas, n_auctions=n_auctions, seed=int(seed))
    s = out["summary"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spend", f"${s['spend']:.2f}", f"of ${budget:.0f}")
    c2.metric("Attributed revenue", f"${s['attributed_revenue']:.2f}")
    c3.metric("ROAS", f"{s['roas']:.2f}", f"target {target_roas:.1f}")
    c4.metric("Eligible auctions", f"{s['eligible_auctions']:,}")
    st.caption(f"Est. incremental revenue: ${out['cannibalization']['incremental_revenue']:.2f} "
               f"(organic overlap {out['cannibalization']['organic_overlap_rate']:.0%})")

    df: pd.DataFrame = out["results"]
    df["cum_spend"] = df["price_paid"].cumsum()
    df["cum_revenue"] = df["attributed_revenue"].cumsum()
    st.subheader("Pacing & revenue over the flight")
    st.line_chart(df[["cum_spend", "cum_revenue"]])

    st.subheader("Per-product performance")
    won = df[df["winner_id"].notna()]
    if not won.empty:
        tbl = (won.groupby("winner_id")
               .agg(spend=("price_paid", "sum"), revenue=("attributed_revenue", "sum"),
                    clicks=("clicked", "sum"), impressions=("winner_id", "size"))
               .reset_index().sort_values("revenue", ascending=False))
        tbl["roas"] = (tbl["revenue"] / tbl["spend"]).round(2)
        st.dataframe(tbl, use_container_width=True)

    st.subheader("Post-flight analysis")
    st.markdown(out["analysis_md"])
else:
    st.info("Tune the campaign in the sidebar, then hit **Run simulation**.")
