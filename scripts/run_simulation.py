"""End-to-end demo: brief -> plan -> auctions -> report.

Briefs can be structured (--category/--budget flags or --brief-json) or
free text (--brief-text, needs ANTHROPIC_API_KEY or OPENAI_API_KEY).
Add --narrate for an LLM-written post-flight recap (falls back to bullets).
"""
import argparse
import json

from auction_sim.catalog import generate_catalog
from auction_sim.simulate import run_campaign


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a simulated sponsored-search campaign.")
    ap.add_argument("--category", default="oat milk")
    ap.add_argument("--budget", type=float, default=500.0)
    ap.add_argument("--objective", default="share_growth", choices=["share_growth", "roas"])
    ap.add_argument("--target-roas", type=float, default=4.0)
    ap.add_argument("--brief-text", default=None,
                    help='Free-text brief, e.g. "grow share in oat milk with $800, keep ROAS above 3"')
    ap.add_argument("--brief-json", default=None,
                    help='Structured brief as JSON, e.g. \'{"category":"pasta","budget":300}\'')
    ap.add_argument("--narrate", action="store_true",
                    help="Use the LLM narrator for the recap (falls back to bullets)")
    ap.add_argument("--n-auctions", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    plan = None
    if args.brief_text:
        from auction_sim.llm.client import get_client
        from auction_sim.llm.planner import plan_from_text
        catalog = generate_catalog(seed=args.seed)
        pres = plan_from_text(args.brief_text, catalog, get_client())
        plan = pres.plan
        print("## Planner rationale\n")
        print(pres.rationale)
        print()
    elif args.brief_json:
        from auction_sim.briefs import plan_from_brief
        catalog = generate_catalog(seed=args.seed)
        plan = plan_from_brief(json.loads(args.brief_json), catalog)

    out = run_campaign(
        category=args.category,
        budget=args.budget,
        objective=args.objective,
        target_roas=args.target_roas,
        n_auctions=args.n_auctions,
        seed=args.seed,
        plan=plan,
    )
    s = out["summary"]
    print(f"Category : {out['plan'].category}  |  Objective: {out['plan'].objective}  "
          f"|  Budget: ${out['plan'].budget:.2f}")
    print(f"Spend    : ${s['spend']:.2f}")
    print(f"Revenue  : ${s['attributed_revenue']:.2f}  (ROAS {s['roas']:.2f})")
    print(f"Funnel   : {s['eligible_auctions']} eligible auctions → {s['clicks']} clicks "
          f"(CTR {s['ctr']:.2%}) → {s['conversions']} conv (CVR {s['cvr']:.2%})")
    print(f"Avg CPC  : ${s['avg_cpc']:.2f}")
    c = out["cannibalization"]
    print(f"Incremental revenue (est.): ${c['incremental_revenue']:.2f} "
          f"(overlap {c['organic_overlap_rate']:.0%})")
    print()

    recap = out["analysis_md"]
    if args.narrate:
        from auction_sim.llm.narrator import narrate_post_flight
        recap, used_llm = narrate_post_flight(
            summary=s, cannibalization=c,
            top_products=out["top_products"], fallback_md=recap)
        if not used_llm:
            print("(LLM narrator unavailable — showing deterministic analysis)\n")
    print(recap)

    with open("report.json", "w") as f:
        json.dump({"args": vars(args), "summary": s,
                   "cannibalization": c,
                   "top_products": out["top_products"]}, f, indent=2)
    print("\nWrote report.json")


if __name__ == "__main__":
    main()
