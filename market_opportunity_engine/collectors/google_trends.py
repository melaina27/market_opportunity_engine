from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import time

from pytrends.request import TrendReq


@dataclass
class TrendSignal:
    keyword: str
    avg_interest: float
    growth_rate: float
    last_interest: float


class GoogleTrendsCollector:
    def __init__(self, hl: str = "en-US", tz: int = 360, retries: int = 3, backoff: float = 1.6):
        self.pytrends = TrendReq(hl=hl, tz=tz)
        self.retries = retries
        self.backoff = backoff

    def fetch_interest(self, keywords: List[str], timeframe: str = "today 3-m") -> List[TrendSignal]:
        out: List[TrendSignal] = []
        for kw in keywords:
            sig = self._fetch_one(kw, timeframe=timeframe)
            if sig:
                out.append(sig)
            time.sleep(0.5)
        return out

    def _fetch_one(self, keyword: str, timeframe: str) -> Optional[TrendSignal]:
        last_err = None
        for i in range(self.retries):
            try:
                self.pytrends.build_payload([keyword], timeframe=timeframe, geo="US")
                df = self.pytrends.interest_over_time()
                if df is None or df.empty or keyword not in df.columns:
                    return None
                s = df[keyword].astype(float)

                avg_interest = float(s.mean())
                last_interest = float(s.iloc[-1])

                n = len(s)
                k = max(3, min(14, n // 4))
                first = float(s.iloc[:k].mean())
                last = float(s.iloc[-k:].mean())

                growth = 0.0 if first <= 0 else (last - first) / first
                growth_rate = max(0.0, min(1.0, growth))

                return TrendSignal(
                    keyword=keyword,
                    avg_interest=avg_interest,
                    growth_rate=growth_rate,
                    last_interest=last_interest,
                )
            except Exception as e:
                last_err = e
                time.sleep((self.backoff ** i))
        return None
