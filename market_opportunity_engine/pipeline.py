# market_opportunity_engine/pipeline.py
from __future__ import annotations

import os
import pandas as pd

from market_opportunity_engine.collectors.mock_data import load_mock_candidates
from market_opportunity_engine.scoring.demand import demand_score
from market_opportunity_engine.scoring.pain import pain_score
from market_opportunity_engine.scoring.competition import competition_score
from market_opportunity_engine.scoring.monetization import monetization_score
from market_opportunity_engine.scoring.opportunity import opportunity_score
from market_opportunity_engine.nlp.extract_pain_points import top_pains


def execution_cost_proxy(kind: str) -> float:
    """
    Simple proxy:
    - physical: harder due to sourcing, shipping, returns
    - digital: easier to iterate and deliver
    """
    kind = (kind or "").lower().strip()
    if kind == "physical":
        return 1.20
    if kind == "digital":
        return 0.90
    return 1.10


def main() -> None:
    candidates = load_mock_candidates()
    rows = []

    for c in candidates:
        d = demand_score(c.search_volume, c.growth_rate, c.intent_score)
        p = pain_score(c.snippets)
        comp = competition_score(c.top10_review_median, c.brand_concentration)
        m = monetization_score(c.price_usd, c.est_cogs_usd, c.platform_fee_rate, c.fulfillment_cost_usd)
        exe = execution_cost_proxy(c.kind)

        opp = opportunity_score(demand=d, pain=p, monetization=m, competition=comp, execution_cost=exe)

        pains = top_pains(c.snippets, k=3)
        top_pain_str = "; ".join([f"{k}:{v}" for k, v in pains]) if pains else ""

        rows.append({
            "candidate_id": c.candidate_id,
            "kind": c.kind,
            "title": c.title,
            "keyword": c.keyword,
            "price_usd": c.price_usd,
            "search_volume": c.search_volume,
            "growth_rate": c.growth_rate,
            "intent_score": c.intent_score,
            "top10_review_median": c.top10_review_median,
            "brand_concentration": c.brand_concentration,
            "demand_score": round(d, 4),
            "pain_score": round(p, 4),
            "competition_score": round(comp, 4),
            "monetization_score": round(m, 4),
            "execution_cost": round(exe, 3),
            "opportunity_score": round(opp, 6),
            "top_pains": top_pain_str,
        })

    df = pd.DataFrame(rows).sort_values("opportunity_score", ascending=False).reset_index(drop=True)

    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ranked_products.csv")
    df.to_csv(out_path, index=False)

    print("✅ Done. Ranked opportunities saved to:", out_path)
    print(df[["candidate_id", "kind", "price_usd", "opportunity_score", "title"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
