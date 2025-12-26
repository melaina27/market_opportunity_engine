from __future__ import annotations

import os
import re
import pandas as pd

from market_opportunity_engine.collectors.reddit_search import RedditCollector, filter_relevant
from market_opportunity_engine.scoring.pain_reddit import score_posts


def _find_input(base_dir: str) -> str:
    """
    Auto-detect input keyword list.
    Priority:
      1) opportunity_rank_all.csv (has kind)
      2) opportunity.csv
      3) trends_candidates.csv
    """
    cand = [
        os.path.join(base_dir, "output", "opportunity_rank_all.csv"),
        os.path.join(base_dir, "output", "opportunity.csv"),
        os.path.join(base_dir, "output", "trends_candidates.csv"),
    ]
    for p in cand:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        "No input file found. Expect one of:\n"
        "- output/opportunity_rank_all.csv\n"
        "- output/opportunity.csv\n"
        "- output/trends_candidates.csv\n"
        "Run your trends/opportunity pipeline first."
    )


def _infer_mode(keyword: str, kind: str | None = None) -> str:
    """
    Decide whether to score by pain (digital) or need (physical).
    """
    if kind:
        k = kind.strip().lower()
        if k in ("digital", "physical"):
            return k

    kw = (keyword or "").lower()
    # Heuristic: resume/template/doc keywords => digital
    if any(x in kw for x in ["resume", "cv", "cover letter", "template", "google docs", "docs template"]):
        return "digital"
    return "physical"


def main() -> None:
    base_dir = os.path.dirname(__file__)
    in_path = _find_input(base_dir)

    df_in = pd.read_csv(in_path)

    # Find keyword column
    if "keyword" not in df_in.columns:
        raise ValueError(f"Input file missing 'keyword' column: {in_path}")

    # Optional kind column
    kind_col = "kind" if "kind" in df_in.columns else None

    keywords = df_in["keyword"].astype(str).tolist()

    rows = []
    # Use one collector instance, but toggle topic_filter per keyword (digital off, physical on)
    for kw in keywords[:80]:  # you can raise this later
        mode = _infer_mode(kw, df_in.loc[df_in["keyword"] == kw, kind_col].iloc[0] if kind_col else None)

        # For digital, do NOT apply topic filter (otherwise resumes/jobs subs get killed)
        # For physical, keep topic filter to avoid coupon/deals spam.
        reddit = RedditCollector(
            sleep_s=1.2,
            topic_filter=(mode == "physical"),
        )

        raw = reddit.search(kw, limit=60, sort="relevance", t="year")
        posts = filter_relevant(raw, kw)

        final_score, hits, urls, pain_raw, need_raw = score_posts(posts, mode=mode)

        rows.append(
            {
                "keyword": kw,
                "mode": mode,
                # Keep compatibility: downstream merge expects a "pain_score" column.
                # Here pain_score means "reddit_score used for opportunity" (pain for digital, need for physical).
                "pain_score": round(final_score, 6),
                "pain_raw": pain_raw,
                "need_raw": need_raw,
                "reddit_posts_raw": len(raw),
                "reddit_posts_relevant": len(posts),
                "top_urls": " | ".join(urls),
            }
        )

    out = pd.DataFrame(rows).sort_values("pain_score", ascending=False).reset_index(drop=True)
    out_path = os.path.join(base_dir, "output", "reddit_pain.csv")
    out.to_csv(out_path, index=False)

    print("✅ Done. Saved:", out_path)
    cols = ["keyword", "mode", "pain_score", "pain_raw", "need_raw", "reddit_posts_raw", "reddit_posts_relevant"]
    print(out[cols].head(30).to_string(index=False))


if __name__ == "__main__":
    main()
