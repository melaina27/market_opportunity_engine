# market_opportunity_engine/scoring/channel_recommender.py

import re


def _extract_subreddits_from_top_urls(top_urls: str):
    """
    top_urls 里通常是：
    https://www.reddit.com/r/DIY/comments/... | https://www.reddit.com/r/OrganizationPorn/comments/...
    我们从里面抓 /r/<sub>/ 作为“渠道线索”
    """
    if not top_urls:
        return set()
    subs = set()
    for m in re.finditer(r"reddit\.com/r/([A-Za-z0-9_]+)/", top_urls):
        subs.add(m.group(1).lower())
    return subs


def recommend_channel(row):
    """
    返回：
    (best_channel, sell_mode, price_range, competition_level, channel_fit_score)
    channel_fit_score: 0~1
    """
    keyword = (row.get("keyword") or "").lower()
    kind = (row.get("kind") or "unknown").lower()
    pain = float(row.get("pain_score") or 0.0)
    avg_interest = float(row.get("avg_interest") or 0.0)
    top_urls = row.get("top_urls") or ""

    subs = _extract_subreddits_from_top_urls(top_urls)

    # 默认值
    best_channel = "amazon"
    sell_mode = "physical"
    price_range = "$15–$25"
    competition = "mid"
    score = 0.45

    # --- digital ---
    if kind == "digital":
        best_channel = "gumroad"
        sell_mode = "download"
        price_range = "$9–$29"
        competition = "mid"
        score = 0.55

        # 痛点越高，越可能愿意付费
        if pain >= 0.25:
            score += 0.15
        if pain >= 0.50:
            score += 0.10

        # 有“做项目/做SaaS”的社区信号
        if any(s in subs for s in ["sideproject", "saas", "entrepreneur", "startups"]):
            best_channel = "saas"
            sell_mode = "subscription"
            price_range = "$5–$15/mo"
            score += 0.15

        # 搜索需求很高（avg_interest高）但痛点一般：更像“流量品”，适合 SEO + 模板站
        if avg_interest >= 40 and pain < 0.25:
            best_channel = "seo_site"
            sell_mode = "lead + upsell"
            price_range = "Free → $19–$49"
            competition = "high"
            score -= 0.05

        return best_channel, sell_mode, price_range, competition, max(min(score, 1.0), 0.0)

    # --- physical ---
    if kind == "physical":
        sell_mode = "physical"

        # 3Dprinting / setup 类社区：适合 Etsy（定制/小众/设计感）或 Amazon（标准化）
        if any(s in subs for s in ["3dprinting", "organizationporn", "desksetup", "battlestations", "cablemanagement", "deskcablemanagement"]):
            best_channel = "etsy"
            price_range = "$20–$45"
            competition = "mid"
            score += 0.20

        # 工具/家装/DIY：也适合 Amazon（标准化大货）
        if any(s in subs for s in ["diy", "tools", "askelectricians", "homeimprovement"]):
            best_channel = "amazon"
            price_range = "$12–$29"
            competition = "high" if avg_interest >= 30 else "mid"
            score += 0.05

        # 搜索需求特别大：Amazon 红海风险提高
        if avg_interest >= 40:
            if best_channel == "amazon":
                competition = "high"
                score -= 0.10
            else:
                # Etsy 也会变红，但仍可能靠差异化活
                competition = "mid-high"
                score -= 0.05

        # 痛点高：更容易靠“改良版/升级版”卖更贵
        if pain >= 0.50:
            score += 0.10
            price_range = "$25–$60" if best_channel == "etsy" else price_range

        return best_channel, sell_mode, price_range, competition, max(min(score, 1.0), 0.0)

    # --- unknown ---
    # 未分类：保守给一个中性渠道
    sell_mode = "mixed"
    best_channel = "amazon"
    competition = "mid"
    score = 0.35 + 0.30 * min(pain, 1.0)
    if avg_interest < 10:
        score -= 0.10

    return best_channel, sell_mode, price_range, competition, max(min(score, 1.0), 0.0)
