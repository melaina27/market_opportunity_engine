# market_opportunity_engine/scoring/demand.py
from __future__ import annotations

def demand_score(search_volume: int, growth_rate: float, intent_score: float) -> float:
    """
    Demand score in [0, 1.5] roughly.
    We normalize volume with a soft log-like scale.
    """
    # volume normalization: 0..100k => 0..1 (cap)
    vol_norm = min(1.0, search_volume / 100_000.0)
    # growth: cap at 0.5 for stability
    growth_norm = min(0.5, max(0.0, growth_rate))
    # intent already 0..1
    return (0.55 * vol_norm) + (0.25 * (growth_norm / 0.5)) + (0.20 * intent_score)
