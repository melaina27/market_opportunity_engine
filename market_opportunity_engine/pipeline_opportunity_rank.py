# market_opportunity_engine/pipeline_opportunity_rank.py

import os
import ast
import pandas as pd

from market_opportunity_engine.scoring.trend_lifecycle import classify_stage
from market_opportunity_engine.scoring.channel_recommender import recommend_channel


DIGITAL_HINTS = [
    "template", "resume", "google docs", "canva", "cv", "cover letter", "builder"
]

PHYSICAL_HINTS = [
    "organizer", "cord", "wire", "cable", "desk mat", "desk pad", "clip", "box"
]


def classify_kind(keyword: str) -> str:
    k = (keyword or "").lower()
    if any(h in k for h in DIGITAL_HINTS):
        return "digital"
    if any(h in k for h in PHYSICAL_HINTS):
        return "physical"
    return "unknown"


def _parse_series_cell(x):
    """
    Parse a CSV cell that may represent a weekly interest series.
    Accepts:
      - Python literal list/tuple string: "[1,2,3]"
      - Comma-separated string: "1,2,3"
      - Already a list
    Returns list[float] or None.
    """
    if x is None:
        return None
    if isinstance(x, list):
        return x
    if isinstance(x, float) and pd.isna(x):
        return None

    s = str(x).strip()
    if not s:
        return None

    try:
        v = ast.literal_eval(s)
        if isinstance(v, (list, tuple)):
            return [float(i) for i in v]
    except Exception:
        pass

    if "," in s:
        parts = [p.strip() for p in s.split(",") if p.strip()]
        try:
            return [float(p) for p in parts]
        except Exception:
            return None

    return None


def _safe_classify_stage(series):
    try:
        return classify_stage(series or [])
    except Exception:
        return ("未知", None)


def _normalize_reco(reco) -> dict:
    """
    Make recommend_channel output robust.
    Supports:
      - dict / pandas.Series
      - tuple/list: (best_channel, sell_mode, price_range, competition_level, channel_fit_score)
      - None / others -> {}
    Also maps common alias keys to canonical keys.
    """
    if reco is None:
        return {}

    if isinstance(reco, pd.Series):
        d = reco.to_dict()
    elif isinstance(reco, dict):
        d = dict(reco)
    elif isinstance(reco, (list, tuple)) and len(reco) >= 5:
        d = {
            "best_channel": reco[0],
            "sell_mode": reco[1],
            "price_range": reco[2],
            "competition_level": reco[3],
            "channel_fit_score": reco[4],
        }
    else:
        return {}

    # alias mapping (in case your recommender uses different field names)
    alias = {
        "best_channel": ["best_channel", "channel", "platform", "marketplace", "best_platform", "best_marketplace"],
        "sell_mode": ["sell_mode", "mode", "selling_mode"],
        "price_range": ["price_range", "price", "pricing", "price_band"],
        "competition_level": ["competition_level", "competition", "competition_score", "comp_level"],
        "channel_fit_score": ["channel_fit_score", "fit", "fit_score", "score", "channel_score"],
    }

    out = {}
    for canon, keys in alias.items():
        for k in keys:
            if k in d and d[k] is not None:
                out[canon] = d[k]
                break

    # ensure types
    if "channel_fit_score" in out:
        out["channel_fit_score"] = pd.to_numeric(out["channel_fit_score"], errors="coerce")

    return out


def main() -> None:
    base_dir = os.path.dirname(__file__)
    trends_path = os.path.join(base_dir, "output", "trends_candidates.csv")
    pain_path = os.path.join(base_dir, "output", "reddit_pain.csv")

    if not os.path.exists(trends_path):
        raise FileNotFoundError(f"missing input: {trends_path}. run pipeline_trends_expand first.")
    if not os.path.exists(pain_path):
        raise FileNotFoundError(f"missing input: {pain_path}. run pipeline_reddit_pain first.")

    t = pd.read_csv(trends_path)
    p = pd.read_csv(pain_path)

    df = t.merge(
        p[["keyword", "pain_score", "reddit_posts_relevant", "top_urls"]],
        on="keyword",
        how="left",
    )

    df["pain_score"] = df["pain_score"].fillna(0.0)
    df["reddit_posts_relevant"] = df["reddit_posts_relevant"].fillna(0).astype(int)
    df["top_urls"] = df["top_urls"].fillna("")

    df["kind"] = df["keyword"].astype(str).apply(classify_kind)

    # ========= 趋势寿命预测（可选列：week_interest_series） =========
    if "week_interest_series" in df.columns:
        df["week_interest_series"] = df["week_interest_series"].apply(_parse_series_cell)
        stage_df = df["week_interest_series"].apply(lambda s: pd.Series(_safe_classify_stage(s)))
        stage_df.columns = ["trend_stage", "peak_weeks"]
        df = pd.concat([df, stage_df], axis=1)
    else:
        df["trend_stage"] = "未知"
        df["peak_weeks"] = None

    # ========= different demand floors =========
    df["demand_floor_physical"] = (df["avg_interest"] >= 8).astype(int)
    df["demand_floor_digital"] = ((df["avg_interest"] >= 4) | (df["pain_score"] >= 0.25)).astype(int)

    # ========= opp_score =========
    def compute_opp(row):
        base = row["trend_score"] * (0.35 + 0.65 * row["pain_score"])
        if row["kind"] == "physical":
            return base * row["demand_floor_physical"]
        if row["kind"] == "digital":
            return base * row["demand_floor_digital"]
        return base * (row["avg_interest"] >= 10)

    df["opp_score"] = df.apply(compute_opp, axis=1)

    # ========= 渠道推荐 =========
    rec_df = df.apply(lambda r: pd.Series(_normalize_reco(recommend_channel(r))), axis=1)
    df = pd.concat([df, rec_df], axis=1)

    # ========= 兜底：避免缺列导致后续计算挂 =========
    if "channel_fit_score" not in df.columns:
        df["channel_fit_score"] = 0.5
    df["channel_fit_score"] = pd.to_numeric(df["channel_fit_score"], errors="coerce").fillna(0.5)

    if "competition_level" not in df.columns:
        df["competition_level"] = "unknown"
    df["competition_level"] = df["competition_level"].fillna("unknown")

    if "best_channel" not in df.columns:
        df["best_channel"] = "unknown"
    df["best_channel"] = df["best_channel"].fillna("unknown")

    if "price_range" not in df.columns:
        df["price_range"] = ""
    df["price_range"] = df["price_range"].fillna("")

    if "sell_mode" not in df.columns:
        df["sell_mode"] = "unknown"
    df["sell_mode"] = df["sell_mode"].fillna("unknown")

    # ========= money_score =========
    def margin_proxy(row):
        if row.get("kind") == "digital":
            return 1.15
        if str(row.get("best_channel", "")).lower() == "etsy":
            return 1.10
        return 1.00

    def competition_penalty(level: str):
        level = (level or "").lower()
        if level == "high":
            return 0.75
        if level in ("mid-high", "midhigh", "mid_high"):
            return 0.82
        if level == "mid":
            return 0.92
        return 1.00

    df["money_score"] = (
        df["opp_score"]
        * df["channel_fit_score"]
        * df.apply(margin_proxy, axis=1)
        * df["competition_level"].apply(competition_penalty)
    )

    # ========= 可选：更狠的“短期赚钱过滤”开关 =========
    FILTER_FOR_MONEY = False
    if FILTER_FOR_MONEY:
        df = df[(df["trend_stage"] == "加速期")]
        df = df[(df["pain_score"] >= 0.20)]
        df = df[(df["avg_interest"] >= 8)]

    # ========= 排序输出 =========
    df_all = df.sort_values("money_score", ascending=False).reset_index(drop=True)
    df_physical = df[df["kind"] == "physical"].sort_values("money_score", ascending=False).reset_index(drop=True)
    df_digital = df[df["kind"] == "digital"].sort_values("money_score", ascending=False).reset_index(drop=True)

    out_all = os.path.join(base_dir, "output", "opportunity_rank_all.csv")
    out_phy = os.path.join(base_dir, "output", "opportunity_rank_physical.csv")
    out_dig = os.path.join(base_dir, "output", "opportunity_rank_digital.csv")

    df_all.to_csv(out_all, index=False)
    df_physical.to_csv(out_phy, index=False)
    df_digital.to_csv(out_dig, index=False)

    print("✅ Saved:")
    print(" -", out_all)
    print(" -", out_phy)
    print(" -", out_dig)

    cols = [
        "keyword", "kind",
        "trend_score", "pain_score", "avg_interest", "growth_rate", "reddit_posts_relevant",
        "trend_stage", "peak_weeks",
        "best_channel", "sell_mode", "price_range", "competition_level", "channel_fit_score",
        "opp_score", "money_score",
    ]
    show_cols = [c for c in cols if c in df_all.columns]

    print("\n=== TOP 10 (ALL) ===")
    print(df_all[show_cols].head(10).to_string(index=False))
    print("\n=== TOP 10 (PHYSICAL) ===")
    print(df_physical[show_cols].head(10).to_string(index=False))
    print("\n=== TOP 10 (DIGITAL) ===")
    print(df_digital[show_cols].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
