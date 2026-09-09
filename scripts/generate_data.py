"""Dump the synthetic catalog + query plan to data/ for inspection."""
import argparse
from pathlib import Path

from auction_sim.catalog import generate_catalog, query_plan


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-products", type=int, default=240)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    catalog = generate_catalog(n_products=args.n_products, seed=args.seed)
    catalog.to_csv(outdir / "catalog.csv", index=False)
    query_plan(catalog, seed=args.seed).to_csv(outdir / "queries.csv", index=False)
    print(f"Wrote {outdir/'catalog.csv'} and {outdir/'queries.csv'}")


if __name__ == "__main__":
    main()
