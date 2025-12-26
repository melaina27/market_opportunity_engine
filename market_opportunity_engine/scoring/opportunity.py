# market_opportunity_engine/scoring/opportunity.py
from __future__ import annotations

def opportunity_score(demand: float, pain: float, monetization: float, competition: float, execution_cost: float) -> float:
    """
    Company-style opportunity score.
    Higher is better.

    execution_cost: proxy in [0.8..1.3] (higher = harder)
      physical tends to be higher due to logistics.
    """
    denom = max(0.3, competition * max(0.5, execution_cost))
    return (demand * pain * monetization) / denom
