# market_opportunity_engine/scoring/competition.py
from __future__ import annotations

def competition_score(top10_review_median: int, brand_concentration: float) -> float:
    """
    competition_score in [0.3, 2.0] roughly (higher is worse).
    """
    # review intensity normalization: 0..30k => 0..1
    review_norm = min(1.0, top10_review_median / 30_000.0)
    # brand concentration already 0..1
    base = 0.6 + 0.9 * review_norm + 0.5 * max(0.0, min(1.0, brand_concentration))
    return max(0.3, min(2.0, base))
