from __future__ import annotations

import os
import pandas as pd

from market_opportunity_engine.collectors.google_trends import GoogleTrendsCollector
from market_opportunity_engine.collectors.trends_expand import TrendsExpander


SEED_KEYWORDS = [
    "travel toiletry bag",
    "air fryer accessories",
    "desk organizer",
    "resume template",
    "cable organizer",
]

BUY_INTENT_HINTS = [
    "best", "review", "vs", "for", "kit", "set", "accessories", "replacement", "filter",
    "template", "planner", "organizer", "bag", "mat"
]


def looks_buy_intent(q: str) -> bool:
    q = (q or "").lower()
    return any(h in q for h in BUY_INTENT_HINTS)


def main() -> None:
    expander = TrendsExpander(
        sleep_s=1.2,
        jitter_s=0.8,
        retries=6,
        backoff_base=2.0,
        cache_path="market_opportunity_engine/output/trends_related_cache.json",
    )

    related = expander.expand(
        SEED_KEYWORDS,
        timeframe="today 12-m",
        geo="US",
        max_per_seed=10,
        kinds=("top", "rising"),
    )

    candidates = [r.keyword for r in related if looks_buy_intent(r.keyword)]
    candidates = list(dict.fromkeys(candidates))  # stable dedup

    print(f"Expanded keywords: {len(related)} | After intent filter: {len(candidates)}")

    collector = GoogleTrendsCollector()
    # IMPORTANT: Trends can also 429, so keep candidate list modest initially
    candidates = candidates[:60]
    signals = collector.fetch_interest(candidates, timeframe="today 3-m")

    rows = []
    for s in signals:
        score = (0.70 * s.growth_rate) + (0.30 * (s.avg_interest / 100.0))
        rows.append({
            "keyword": s.keyword,
            "avg_interest": round(s.avg_interest, 2),
            "last_interest": round(s.last_interest, 2),
            "growth_rate": round(s.growth_rate, 4),
            "trend_score": round(score, 6),
        })

    df = pd.DataFrame(rows).sort_values("trend_score", ascending=False).reset_index(drop=True)

    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "trends_candidates.csv")
    df.to_csv(out_path, index=False)

    print("✅ Done. Saved:", out_path)
    print(df.head(30).to_string(index=False))


if __name__ == "__main__":
    main()
