# market_opportunity_engine/scoring/monetization.py
from __future__ import annotations

def monetization_score(
    price_usd: float,
    est_cogs_usd: float,
    platform_fee_rate: float,
    fulfillment_cost_usd: float,
) -> float:
    """
    monetization_score in [0, 1]
    Based on margin % and absolute margin.
    """
    fee = price_usd * max(0.0, platform_fee_rate)
    gross_profit = price_usd - est_cogs_usd - fee - fulfillment_cost_usd
    if price_usd <= 0:
        return 0.0
    margin_pct = gross_profit / price_usd  # can be negative

    # normalize:
    # margin_pct: -0.2..0.8 => 0..1
    margin_norm = (margin_pct + 0.2) / 1.0
    margin_norm = max(0.0, min(1.0, margin_norm))

    # absolute profit: 0..30 => 0..1
    abs_norm = max(0.0, min(1.0, gross_profit / 30.0))

    return 0.6 * margin_norm + 0.4 * abs_norm
