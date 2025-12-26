from __future__ import annotations

import re
from typing import Dict, List, Tuple, Optional

from market_opportunity_engine.collectors.reddit_search import RedditPost

# === Pain words (complaints) ===
PAIN_PATTERNS = [
    r"\bproblem\b",
    r"\bissue\b",
    r"\bfrustrat\w*\b",
    r"\bannoy\w*\b",
    r"\bhate\b",
    r"\bdisappoint\w*\b",
    r"\bscam\b",
    r"\bfake\b",
    r"\bcheap\b",
    r"\bpoor quality\b",
    r"\bquality control\b",
    r"\breturn(ed)?\b",
    r"\brefund(ed)?\b",
    r"\bwaste of money\b",
    r"\bavoid\b",
]
PAIN_RE = re.compile("|".join(PAIN_PATTERNS), re.IGNORECASE)

# === Need words (request / how-to / recommendation intent) ===
NEED_PATTERNS = [
    r"\bany recommendations\b",
    r"\brecommend(ation|ations|ed|s)?\b",
    r"\bwhat should i buy\b",
    r"\bwhich (one|brand|product)\b",
    r"\bhelp\b",
    r"\bhow do i\b",
    r"\bhow to\b",
    r"\bideas?\b",
    r"\bsuggest(ion|ions|ed|s)?\b",
    r"\balternative(s)?\b",
    r"\blooking for\b",
    r"\bbest way\b",
    r"\bneed\b",
]
NEED_RE = re.compile("|".join(NEED_PATTERNS), re.IGNORECASE)


def _confidence(n: int, cap: int = 12) -> float:
    """Penalize tiny sample sizes so 1-2 posts won't dominate ranking."""
    if n <= 0:
        return 0.0
    return max(0.15, min(1.0, n / float(cap)))


def _norm(per_post: float, lo: float, hi: float) -> float:
    """Normalize per-post hit-rate into [0,1] using a soft linear band."""
    if hi <= lo:
        return 0.0
    x = (per_post - lo) / (hi - lo)
    return max(0.0, min(1.0, x))


def score_posts(
    posts: List[RedditPost],
    mode: Optional[str] = None,
) -> Tuple[float, Dict[str, int], List[str], float, float]:
    """
    Returns:
    - final_score: 0..1 (used for merge as pain_score)
    - hits: dict of pattern hit counts (combined pain+need, for debugging)
    - example_urls: up to 3 post urls
    - pain_raw: 0..1 (complaint intensity)
    - need_raw: 0..1 (request/recommendation intensity)

    mode:
      - "digital": favor pain_raw
      - "physical": favor need_raw
      - None/"auto": default favor pain_raw
    """
    if not posts:
        return 0.0, {}, [], 0.0, 0.0

    hits: Dict[str, int] = {}
    pain_total = 0
    need_total = 0

    for p in posts:
        text = (p.title + " " + p.selftext).strip()

        pm = PAIN_RE.findall(text)
        nm = NEED_RE.findall(text)

        pain_total += len(pm)
        need_total += len(nm)

        for w in pm:
            k = str(w).lower()
            hits[k] = hits.get(k, 0) + 1
        for w in nm:
            k = str(w).lower()
            hits[k] = hits.get(k, 0) + 1

    n = len(posts)
    pain_per_post = pain_total / max(1, n)
    need_per_post = need_total / max(1, n)

    # pain: 0.2 hit/post noticeable; 1.5 hit/post very strong
    pain_raw = _norm(pain_per_post, lo=0.2, hi=1.5)
    # need: 0.15 hit/post noticeable; 1.2 hit/post strong
    need_raw = _norm(need_per_post, lo=0.15, hi=1.2)

    conf = _confidence(n, cap=12)

    mode_l = (mode or "auto").lower()
    if mode_l == "physical":
        base = need_raw
    else:
        # "digital" / "auto" / None -> pain
        base = pain_raw

    final_score = round(base * conf, 6)

    example_urls = [
        p.url
        for p in sorted(posts, key=lambda x: (x.score, x.num_comments), reverse=True)[:3]
    ]
    return final_score, hits, example_urls, round(pain_raw, 6), round(need_raw, 6)
