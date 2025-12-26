# market_opportunity_engine/scoring/pain.py
from __future__ import annotations

from typing import List
from market_opportunity_engine.nlp.extract_pain_points import extract_pain_counts
from market_opportunity_engine.nlp.sentiment import aggregate_negative_sentiment


def pain_score(snippets: List[str]) -> float:
    """
    pain_score in [0, 1]
    - frequency proxy: number of pain matches per snippet
    - severity proxy: negative sentiment magnitude
    """
    if not snippets:
        return 0.0

    counts = extract_pain_counts(snippets)
    total_hits = sum(counts.values())
    # average hits per snippet, cap at 2.0
    freq = min(2.0, total_hits / max(1, len(snippets)))
    freq_norm = freq / 2.0

    severity = aggregate_negative_sentiment(snippets)  # 0..1

    return 0.55 * freq_norm + 0.45 * severity
