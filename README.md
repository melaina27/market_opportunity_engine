# Market Opportunity Engine
A data-driven engine for discovering profitable physical & digital product opportunities.

Built by Melaina (UCSD CS) - Quant & Product Engineering Track

## What is this?
market_opportunity_engine is a Python system that discovers high-potential product ideas by combining:
- Google Trends demand signals
- Reddit pain-point mining
- NLP sentiment + pain extraction
- Monetization + competition scoring
- Channel recommendation (Amazon / Etsy / SaaS / SEO sites)

## Project Structure

```text
market_opportunity_engine/
├── collectors/
│   ├── google_trends.py
│   ├── reddit_search.py
│   └── trends_expand.py
├── nlp/
│   ├── extract_pain_points.py
│   └── sentiment.py
├── scoring/
│   ├── demand.py
│   ├── pain.py
│   ├── competition.py
│   ├── monetization.py
│   └── opportunity.py
└── pipeline_opportunity_rank.py



## How to run
```bash
python -m market_opportunity_engine.pipeline_opportunity_rank

