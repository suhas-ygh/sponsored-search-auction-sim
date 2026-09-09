"""Synthetic catalog + query plan generation.

Everything here is fake data for development. No real retailer data is used
anywhere in this project.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CATEGORIES = ["oat milk", "cold brew coffee", "granola", "greek yogurt", "pasta", "salsa"]
BRANDS = ["Northfield", "BlueHarbor", "GoldenAcre", "Pureline",
          "CopperKettle", "Wildroot", "Sunmill", "Alto"]

QUERY_ALIASES = {
    "oat milk": ["oat milk", "oatmilk", "dairy free milk"],
    "cold brew coffee": ["cold brew", "cold brew coffee", "iced coffee"],
    "granola": ["granola", "granola cereal"],
    "greek yogurt": ["greek yogurt", "yogurt"],
    "pasta": ["pasta", "spaghetti", "penne"],
    "salsa": ["salsa", "salsa dip"],
}


def generate_catalog(n_products: int = 240, seed: int = 42) -> pd.DataFrame:
    """One row per product. Returned frame is NOT indexed; index it by
    product_id before passing to the auction."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "product_id": [f"P{i:04d}" for i in range(n_products)],
        "brand": rng.choice(BRANDS, size=n_products),
        "category": rng.choice(CATEGORIES, size=n_products),
        "price": np.round(rng.uniform(2.5, 12.0, n_products), 2),
        "margin_rate": np.round(rng.uniform(0.15, 0.45, n_products), 3),
        "quality": np.round(rng.beta(5, 2, n_products), 3),  # ad relevance in [0,1]
        "base_ctr": np.round(rng.uniform(0.02, 0.12, n_products), 4),
        "base_cvr": np.round(rng.uniform(0.05, 0.30, n_products), 4),
    })
    return df


def query_plan(catalog: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """One row per query string with normalized search volume."""
    rng = np.random.default_rng(seed)
    rows = []
    for cat, aliases in QUERY_ALIASES.items():
        n_cat = int((catalog["category"] == cat).sum())
        for q in aliases:
            rows.append({
                "query": q,
                "category": cat,
                "volume": float(rng.uniform(0.5, 1.5) * max(n_cat, 1)),
            })
    plan = pd.DataFrame(rows)
    plan["volume"] = plan["volume"] / plan["volume"].sum()
    return plan
