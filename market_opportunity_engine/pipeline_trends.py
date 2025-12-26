from __future__ import annotations

import os
import pandas as pd

from market_opportunity_engine.collectors.google_trends import GoogleTrendsCollector


SEED_KEYWORDS = [
    # physical-ish
    "cable organizer",
    "desk organizer",
    "drawer organizer",
    "reusable food storage bag",
    "bento lunch box",
    "pet water fountain filter",
    "dog lick mat",
    "cat grooming glove",
    "air fryer accessories",
    "travel toiletry bag",
    # digital-ish
    "notion budget planner template",
    "notion habit tracker template",
    "resume template",
    "job application tracker spreadsheet",
    "study planner template",
    "meal planner template",
]


def main() -> None:
    collector = GoogleTrendsCollector()
    signals = collector.fetch_interest(SEED_KEYWORDS, timeframe="today 3-m")

    rows = []
    for s in signals:
        # simple ranking score: prefer growth + decent baseline interest
        score = (0.65 * s.growth_rate) + (0.35 * (s.avg_interest / 100.0))
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
    out_path = os.path.join(out_dir, "trends_ranked.csv")
    df.to_csv(out_path, index=False)

    print("✅ Done. Trends ranked saved to:", out_path)
    print(df.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
