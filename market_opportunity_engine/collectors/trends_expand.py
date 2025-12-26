from __future__ import annotations

from dataclasses import dataclass
from typing import List, Set, Dict, Any, Optional, Tuple
import time
import random
import json
import os

from pytrends.request import TrendReq
from pytrends import exceptions as pt_ex


@dataclass
class RelatedKeyword:
    keyword: str
    source_seed: str
    kind: str  # "top" or "rising"


class TrendsExpander:
    def __init__(
        self,
        hl: str = "en-US",
        tz: int = 360,
        sleep_s: float = 1.2,
        jitter_s: float = 0.8,
        retries: int = 6,
        backoff_base: float = 2.0,
        cache_path: str = "market_opportunity_engine/output/trends_related_cache.json",
        cache_ttl_s: int = 12 * 3600,
    ):
        self.pytrends = TrendReq(hl=hl, tz=tz)
        self.sleep_s = float(sleep_s)
        self.jitter_s = float(jitter_s)
        self.retries = int(retries)
        self.backoff_base = float(backoff_base)
        self.cache_path = cache_path
        self.cache_ttl_s = int(cache_ttl_s)

        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        self._cache: Dict[str, Any] = self._load_cache()

    def expand(
        self,
        seeds: List[str],
        timeframe: str = "today 12-m",
        geo: str = "US",
        max_per_seed: int = 15,
        kinds: Tuple[str, ...] = ("top", "rising"),
    ) -> List[RelatedKeyword]:
        out: List[RelatedKeyword] = []
        seen: Set[str] = set()

        for seed in seeds:
            cached = self._get_cached(seed, timeframe, geo, max_per_seed, kinds)
            if cached is None:
                items = self._fetch_related(seed, timeframe, geo, max_per_seed, kinds)
                self._set_cached(seed, timeframe, geo, max_per_seed, kinds, items)
                self._save_cache()
                cached = items

            for item in cached:
                kw = (item.get("keyword") or "").strip().lower()
                if not kw or kw in seen:
                    continue
                seen.add(kw)
                out.append(RelatedKeyword(keyword=kw, source_seed=item["source_seed"], kind=item["kind"]))

            self._sleep_gently()

        return out

    def _fetch_related(
        self,
        seed: str,
        timeframe: str,
        geo: str,
        max_per_seed: int,
        kinds: Tuple[str, ...],
    ) -> List[Dict[str, str]]:
        for attempt in range(self.retries):
            try:
                self.pytrends.build_payload([seed], timeframe=timeframe, geo=geo)
                rel = self.pytrends.related_queries()
                if not rel or seed not in rel:
                    return []

                items: List[Dict[str, str]] = []
                for kind in kinds:
                    df = rel[seed].get(kind)
                    if df is None or df.empty or "query" not in df.columns:
                        continue
                    for q in df["query"].head(max_per_seed).astype(str).tolist():
                        qn = q.strip().lower()
                        if qn:
                            items.append({"keyword": qn, "source_seed": seed, "kind": kind})

                return items

            except pt_ex.TooManyRequestsError:
                wait = (self.backoff_base ** attempt) + random.random() * 2.0
                print(f"⚠️ 429 for seed='{seed}'. backoff {wait:.1f}s (attempt {attempt+1}/{self.retries})")
                time.sleep(wait)

            except Exception as e:
                wait = 1.5 + random.random() * 1.5
                print(f"⚠️ error seed='{seed}': {e}. retry in {wait:.1f}s")
                time.sleep(wait)

        print(f"❌ Failed after retries seed='{seed}'")
        return []

    def _sleep_gently(self) -> None:
        time.sleep(self.sleep_s + random.random() * self.jitter_s)

    def _cache_key(self, seed: str, timeframe: str, geo: str, max_per_seed: int, kinds: Tuple[str, ...]) -> str:
        payload = {
            "seed": seed,
            "timeframe": timeframe,
            "geo": geo,
            "max_per_seed": max_per_seed,
            "kinds": list(kinds),
        }
        return json.dumps(payload, sort_keys=True)

    def _load_cache(self) -> Dict[str, Any]:
        if not os.path.exists(self.cache_path):
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cache(self) -> None:
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _get_cached(
        self,
        seed: str,
        timeframe: str,
        geo: str,
        max_per_seed: int,
        kinds: Tuple[str, ...],
    ) -> Optional[List[Dict[str, str]]]:
        key = self._cache_key(seed, timeframe, geo, max_per_seed, kinds)
        obj = self._cache.get(key)
        if not obj:
            return None
        ts = obj.get("ts", 0)
        if (time.time() - ts) > self.cache_ttl_s:
            return None
        return obj.get("items")

    def _set_cached(
        self,
        seed: str,
        timeframe: str,
        geo: str,
        max_per_seed: int,
        kinds: Tuple[str, ...],
        items: List[Dict[str, str]],
    ) -> None:
        key = self._cache_key(seed, timeframe, geo, max_per_seed, kinds)
        self._cache[key] = {"ts": time.time(), "items": items}
