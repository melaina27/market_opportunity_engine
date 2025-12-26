# market_opportunity_engine/collectors/mock_data.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class Candidate:
    """A candidate opportunity (physical or digital) discovered from market signals."""
    candidate_id: str
    kind: str  # "physical" or "digital"
    title: str
    keyword: str

    # demand signals
    search_volume: int                 # monthly-ish volume proxy
    growth_rate: float                 # 0.00~1.00
    intent_score: float                # 0.00~1.00 (how purchase-intent-y the keyword is)

    # competition signals
    top10_review_median: int           # proxy for how crowded
    brand_concentration: float         # 0~1 (higher = more dominated)

    # monetization signals
    price_usd: float
    est_cogs_usd: float                # for digital can be ~0
    platform_fee_rate: float           # 0~1
    fulfillment_cost_usd: float        # for digital can be 0

    # text signals (reviews/posts snippets)
    snippets: List[str]


def load_mock_candidates() -> List[Candidate]:
    """
    Mock dataset so the pipeline is runnable immediately.
    Replace this later with real collectors (Amazon/Reddit/Google/etc).
    """
    return [
        Candidate(
            candidate_id="P001",
            kind="physical",
            title="Desk Cable Management Clips (set of 30)",
            keyword="desk cable organizer clips",
            search_volume=18000,
            growth_rate=0.18,
            intent_score=0.78,
            top10_review_median=7200,
            brand_concentration=0.22,
            price_usd=16.99,
            est_cogs_usd=4.20,
            platform_fee_rate=0.12,
            fulfillment_cost_usd=3.10,
            snippets=[
                "Adhesive is weak, fell off after 2 days.",
                "Works but installation is annoying and messy.",
                "Too small for thicker cables; wish sizes were clearer.",
                "Great idea but quality feels cheap."
            ],
        ),
        Candidate(
            candidate_id="P002",
            kind="physical",
            title="Reusable Silicone Food Storage Bags (6 pack)",
            keyword="reusable silicone food storage bags leakproof",
            search_volume=54000,
            growth_rate=0.10,
            intent_score=0.72,
            top10_review_median=16500,
            brand_concentration=0.41,
            price_usd=29.99,
            est_cogs_usd=9.50,
            platform_fee_rate=0.12,
            fulfillment_cost_usd=4.40,
            snippets=[
                "Hard to clean corners; smell stays.",
                "Seal doesn't fully close; leaks in backpack.",
                "Too bulky in lunchbox; wish it was slimmer."
            ],
        ),
        Candidate(
            candidate_id="P003",
            kind="digital",
            title="Notion Budget Planner Template (Minimalist)",
            keyword="notion budget planner template",
            search_volume=22000,
            growth_rate=0.27,
            intent_score=0.81,
            top10_review_median=950,
            brand_concentration=0.15,
            price_usd=19.00,
            est_cogs_usd=0.30,  # payment processing or minor cost proxy
            platform_fee_rate=0.10,
            fulfillment_cost_usd=0.0,
            snippets=[
                "Setup was confusing; needed a quick start guide.",
                "Love it but wish it had debt payoff tracking.",
                "Some formulas were broken; had to fix myself."
            ],
        ),
        Candidate(
            candidate_id="P004",
            kind="digital",
            title="Interview Prep Pack (LeetCode schedule + templates)",
            keyword="software interview prep schedule template",
            search_volume=9000,
            growth_rate=0.33,
            intent_score=0.86,
            top10_review_median=420,
            brand_concentration=0.10,
            price_usd=39.00,
            est_cogs_usd=0.50,
            platform_fee_rate=0.10,
            fulfillment_cost_usd=0.0,
            snippets=[
                "Too generic; wanted role-specific versions.",
                "Great structure but daily tasks felt overwhelming.",
                "Wish there were tracker sheets and reminders."
            ],
        ),
        Candidate(
            candidate_id="P005",
            kind="physical",
            title="Mini Cordless Milk Frother",
            keyword="portable milk frother rechargeable",
            search_volume=88000,
            growth_rate=0.06,
            intent_score=0.74,
            top10_review_median=24000,
            brand_concentration=0.55,
            price_usd=24.99,
            est_cogs_usd=7.80,
            platform_fee_rate=0.12,
            fulfillment_cost_usd=4.80,
            snippets=[
                "Battery died after a month.",
                "Not powerful enough; takes too long.",
                "Cute but noisy; build quality inconsistent."
            ],
        ),
    ]
