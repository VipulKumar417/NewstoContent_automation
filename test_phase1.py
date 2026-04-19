"""
test_phase1.py — Live test for Phase 1: Key Manager + News Ingestion
Run from project root:  .\venv\Scripts\python test_phase1.py
"""
import json
import sys

# ── 1. Load config & key manager ─────────────────────────────────────────────
print("\n" + "="*60)
print("  EpiCred Phase 1 — Live Test")
print("="*60)

import config
from pipeline.key_manager import gemini_keys, newsdata_keys

print("\n[ 1 ] Key Manager Status")
print("-"*40)
gs = gemini_keys.status()
ns = newsdata_keys.status()
gnews_ok = bool(config.GNEWS_API_KEY and not config.GNEWS_API_KEY.startswith("your_"))

print(f"  Gemini    : {gs['total_keys']} key(s) loaded | available={gs['available']}")
print(f"  NewsData  : {ns['total_keys']} key(s) loaded | available={ns['available']}")
print(f"  GNews     : configured={gnews_ok}")

if not gs['available'] and not ns['available']:
    print("\n  ⚠  No API keys found in .env. Please fill in your keys and retry.")
    sys.exit(1)

# ── 2. News fetch from each source individually ───────────────────────────────
print("\n[ 2 ]  Testing individual sources")
print("-"*40)

from pipeline.news_fetcher import fetch_newsdata, fetch_gnews, fetch_rss

nd_articles  = fetch_newsdata()
gn_articles  = fetch_gnews()
rss_articles = fetch_rss()

print(f"  NewsData.io  → {len(nd_articles):>3} articles")
print(f"  GNews        → {len(gn_articles):>3} articles")
print(f"  RSS feeds    → {len(rss_articles):>3} articles")

# ── 3. Full deduplication + cache ─────────────────────────────────────────────
print("\n[ 3 ]  Full fetch (deduplicate + cache)")
print("-"*40)

from pipeline.news_fetcher import fetch_all_news
articles = fetch_all_news(force=True)
print(f"  Total unique articles cached: {len(articles)}")

if articles:
    print(f"\n  Top 5 articles:")
    for i, a in enumerate(articles[:5], 1):
        print(f"    {i}. [{a['source']}] {a['title'][:70]}{'…' if len(a['title'])>70 else ''}")

# ── 4. Key manager status after fetch ─────────────────────────────────────────
print("\n[ 4 ]  Key Manager status after fetch")
print("-"*40)
print(f"  Gemini    : {gemini_keys.status()}")
print(f"  NewsData  : {newsdata_keys.status()}")

# ── Result ────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
if len(articles) > 0:
    print(f"  ✅  PASS — {len(articles)} articles fetched and cached successfully")
else:
    print("  ⚠  WARNING — 0 articles fetched. Check API key validity and network.")
print("="*60 + "\n")
