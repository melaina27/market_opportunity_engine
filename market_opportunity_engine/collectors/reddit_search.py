from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set, Tuple
import time
import random
import re
import requests


@dataclass
class RedditPost:
    title: str
    selftext: str
    url: str
    score: int
    num_comments: int
    created_utc: float
    subreddit: str


# 这些是“偏好加分”，不是硬过滤
DEFAULT_PREFER_SUBS = [
    "BuyItForLife",
    "battlestations",
    "desksetup",
    "setups",
    "RateMySetup",
    "CableManagement",
    "DeskCableManagement",
    "cableporn",
    "homeoffice",
    "organization",
    "OrganizationPorn",
    "DIY",
    "LifeProTips",
    "ProductReviews",
    "Frugal",
    "homelab",
    "Ubiquiti",
    "PcBuild",
    "PcBuildHelp",
    "mechanicalkeyboards",
    "electronics",
    "maker",
    "Tools",
    "3Dprinting",
    "AskEngineers",
]

# 强垃圾/导流/促销类 sub：直接过滤（名称经常变化，用 pattern）
DEFAULT_DENY_SUB_PATTERNS = [
    # deals / 导流
    r"deal",
    r"discount",
    r"coupon",
    r"promo",
    r"affiliat",
    r"slickdeal",
    r"hotdeal",
    r"bestonlinedeals",
    r"pcpartsales",
    r"vine",
    r"amzreview",
    r"amzn",
    r"reviewrequest",
    r"finds",
    r"giveaway",
    r"referral",
    r"cashback",
    r"couponing",
    # “内容农场/聚合站”常见命名
    r"(?i)info$",       # ElectronicsWhimsyInfo
    r"(?i)hub$",        # GadgetReviewHub
    r"(?i)guides?$",    # HTBuyingGuides
    r"(?i)trader$",     # AMZreviewTrader
    r"(?i)official$",   # 某些品牌官方导流
]

# ✅ 主题相关 sub（按 subreddit 名称判断）
# 目标：只保留桌面/线材/办公/DIY/设备/网络/电脑相关社区，砍掉旅行/酒店/影视等宇宙杂项
DEFAULT_TOPIC_SUB_PATTERN = (
    r"(cable|cord|wire|clip|tie|wrap|sleeve|organizer|management|cableporn|"
    r"desk|setup|setups|battlestation|workspace|office|homeoffice|wfh|"
    r"organization|organizing|diy|maker|3dprint|printing|electronics|"
    r"pcbuild|homelab|network|ubiquiti|audiophile|mechanicalkeyboards|"
    r"monitor|ergonom|tool|garage|workbench)"
)


def _norm_sub(s: str) -> str:
    return (s or "").strip().lower()


def is_denied_sub(subreddit: str, deny_res: List[re.Pattern]) -> bool:
    s = _norm_sub(subreddit)
    if not s:
        return False
    return any(rx.search(s) for rx in deny_res)


def is_topic_sub(subreddit: str, topic_re: Optional[re.Pattern]) -> bool:
    if topic_re is None:
        return True
    s = _norm_sub(subreddit)
    if not s:
        return False
    return bool(topic_re.search(s))


def filter_subreddits(
    posts: List[RedditPost],
    deny_res: Optional[List[re.Pattern]] = None,
    topic_re: Optional[re.Pattern] = None,
) -> List[RedditPost]:
    if not posts:
        return posts

    deny_res = deny_res or []
    out: List[RedditPost] = []
    for p in posts:
        if deny_res and is_denied_sub(p.subreddit, deny_res):
            continue
        if not is_topic_sub(p.subreddit, topic_re):
            continue
        out.append(p)
    return out


def filter_relevant(posts: List[RedditPost], keyword: str) -> List[RedditPost]:
    kw = (keyword or "").strip().lower()
    if not kw:
        return posts

    phrase_re = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)

    tokens = [t for t in re.split(r"\s+", kw) if len(t) >= 4]
    token_res = [re.compile(r"\b" + re.escape(t) + r"\b", re.IGNORECASE) for t in tokens[:3]]

    filtered: List[RedditPost] = []
    for p in posts:
        text = (p.title + " " + p.selftext).lower()
        if phrase_re.search(text):
            filtered.append(p)
            continue
        if token_res and sum(1 for tr in token_res if tr.search(text)) >= 2:
            filtered.append(p)

    return filtered


class RedditCollector:
    """
    Lightweight Reddit search using the public JSON endpoint.
    No API key required, but be gentle with rate limits.
    """

    def __init__(
        self,
        user_agent: str = "market_opportunity_engine/0.1 (by u/anonymous)",
        sleep_s: float = 1.2,
        prefer_subreddits: Optional[List[str]] = None,
        deny_sub_patterns: Optional[List[str]] = None,
        topic_sub_pattern: Optional[str] = DEFAULT_TOPIC_SUB_PATTERN,
        topic_filter: bool = True,
    ):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": user_agent})
        self.sleep_s = float(sleep_s)

        self.prefer_subs: Set[str] = set(_norm_sub(s) for s in (prefer_subreddits or DEFAULT_PREFER_SUBS) if s)

        pats = deny_sub_patterns or DEFAULT_DENY_SUB_PATTERNS
        self.deny_res: List[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in pats if p]

        self.topic_filter = bool(topic_filter)
        self.topic_re: Optional[re.Pattern] = re.compile(topic_sub_pattern, re.IGNORECASE) if (self.topic_filter and topic_sub_pattern) else None

    def _request(self, query: str, limit: int, sort: str, t: str) -> List[RedditPost]:
        url = "https://www.reddit.com/search.json"
        params = {"q": query, "limit": int(limit), "sort": sort, "t": t}
        try:
            r = self.s.get(url, params=params, timeout=20)
        except requests.RequestException:
            return []

        if r.status_code != 200:
            return []

        try:
            data = r.json()
        except Exception:
            return []

        children = (data.get("data") or {}).get("children") or []
        out: List[RedditPost] = []
        for c in children:
            d = c.get("data") or {}
            out.append(
                RedditPost(
                    title=str(d.get("title") or ""),
                    selftext=str(d.get("selftext") or ""),
                    url="https://www.reddit.com" + str(d.get("permalink") or ""),
                    score=int(d.get("score") or 0),
                    num_comments=int(d.get("num_comments") or 0),
                    created_utc=float(d.get("created_utc") or 0.0),
                    subreddit=str(d.get("subreddit") or ""),
                )
            )

        time.sleep(self.sleep_s + random.random() * 0.6)
        return out

    def _rank_posts(self, posts: List[RedditPost]) -> List[RedditPost]:
        if not posts:
            return posts

        def key(p: RedditPost) -> Tuple[int, int]:
            sub = _norm_sub(p.subreddit)
            prefer = 1 if sub in self.prefer_subs else 0
            # 综合热度（比只看 score 更稳）
            popularity = int(p.score) + 2 * int(p.num_comments)
            return (prefer, popularity)

        return sorted(posts, key=key, reverse=True)

    def search(self, keyword: str, limit: int = 30, sort: str = "relevance", t: str = "year") -> List[RedditPost]:
        kw = (keyword or "").strip()
        if not kw:
            return []

        def _post_process(items: List[RedditPost]) -> List[RedditPost]:
            items = filter_relevant(items, kw)
            items = filter_subreddits(items, deny_res=self.deny_res, topic_re=self.topic_re)
            return items

        posts: List[RedditPost] = []

        # stage 1: phrase, t=year
        q1 = f"\"{kw}\""
        posts = _post_process(self._request(q1, limit=limit, sort=sort, t=t))

        # stage 2: phrase, t=all（补量）
        if len(posts) < 10:
            posts2 = _post_process(self._request(q1, limit=limit, sort=sort, t="all"))
            seen = set(p.url for p in posts)
            for p in posts2:
                if p.url not in seen:
                    posts.append(p)
                    seen.add(p.url)

        # stage 3: token OR, t=all（再补量）
        if len(posts) < 10:
            tokens = [tok for tok in re.split(r"\s+", kw.lower()) if len(tok) >= 4][:3]
            if tokens:
                q3 = " OR ".join(tokens)
                posts3 = _post_process(self._request(q3, limit=limit, sort=sort, t="all"))
                seen = set(p.url for p in posts)
                for p in posts3:
                    if p.url not in seen:
                        posts.append(p)
                        seen.add(p.url)

        return self._rank_posts(posts)
