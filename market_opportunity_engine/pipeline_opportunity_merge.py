# market_opportunity_engine/pipeline_opportunity_merge.py

import os
import ast
import pandas as pd

# 你新加的模块：market_opportunity_engine/scoring/trend_lifecycle.py
# 这里用相对导入（因为你是 python -m market_opportunity_engine.xxx 运行）
from market_opportunity_engine.scoring.trend_lifecycle import classify_stage


def _parse_series_cell(x):
    """
    把 CSV 里可能出现的各种格式转成 list[float]
    支持：
    - "[1,2,3]"
    - "1,2,3"
    - 空/NaN
    - 直接是 list
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

    # 优先尝试 literal_eval: "[...]" / "(...)" 之类
    try:
        v = ast.literal_eval(s)
        if isinstance(v, (list, tuple)):
            return [float(i) for i in v]
    except Exception:
        pass

    # fallback: "a,b,c"
    if "," in s:
        parts = [p.strip() for p in s.split(",") if p.strip()]
        try:
            return [float(p) for p in parts]
        except Exception:
            return None

    return None


def _safe_classify_stage(series):
    """
    返回 (trend_stage, peak_weeks)
    """
    try:
        return classify_stage(series or [])
    except Exception:
        return ("未知", None)


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

    # ========= 趋势寿命预测（可选列：week_interest_series） =========
    # 如果 trends_candidates.csv 没有 week_interest_series，就不会报错，会全部标记为 未知
    if "week_interest_series" in df.columns:
        df["week_interest_series"] = df["week_interest_series"].apply(_parse_series_cell)
        stage_df = df["week_interest_series"].apply(lambda s: pd.Series(_safe_classify_stage(s)))
        stage_df.columns = ["trend_stage", "peak_weeks"]
        df = pd.concat([df, stage_df], axis=1)
    else:
        df["trend_stage"] = "未知"
        df["peak_weeks"] = None

    # ========= demand floor =========
    df["demand_floor"] = (df["avg_interest"] >= 8).astype(int)

    # ========= final opp score（权重可调） =========
    df["opp_score"] = (
        df["trend_score"]
        * (0.35 + 0.65 * df["pain_score"])
        * df["demand_floor"]
    )

    df = df.sort_values("opp_score", ascending=False).reset_index(drop=True)

    out_path = os.path.join(base_dir, "output", "opportunity.csv")
    df.to_csv(out_path, index=False)

    print("✅ Saved:", out_path)
    cols = [
        "keyword", "trend_score", "pain_score", "avg_interest", "growth_rate",
        "reddit_posts_relevant", "trend_stage", "peak_weeks", "opp_score"
    ]
    show_cols = [c for c in cols if c in df.columns]
    print(df[show_cols].head(20).to_string(index=False))


if __name__ == "__main__":
    main()
