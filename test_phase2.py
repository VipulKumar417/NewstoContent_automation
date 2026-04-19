import sys
import os

# Ensure the project root is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from pipeline.news_fetcher import load_cache, save_cache
from pipeline.trend_analyzer import analyze_and_filter_articles

print("\n" + "="*60)
print("  EpiCred Phase 2 — Trend Analyzer Test")
print("="*60)

articles = load_cache()
if not articles:
    print("⚠ No articles in cache! Run Phase 1 first.")
    sys.exit(1)

print(f"\n[ 1 ] Loaded {len(articles)} articles from cache.")
print("-"*40)

# We will just analyze the first 5 articles so we don't blow through rate limits
articles_to_test = articles[:5]
print(f"Scoring {len(articles_to_test)} articles...")

recommended = analyze_and_filter_articles(articles_to_test)

# Save back to cache to persist the scores first!
save_cache(articles)

print("\n" + "="*60)
print(f"  DONE: {len(recommended)} articles recommended (Score >= 7)")
print("="*60)

for idx, art in enumerate(recommended, 1):
    try:
        score = art.get("score", {})
        print(f"\n{idx}. {art.get('title')}".encode('ascii', 'replace').decode('ascii'))
        print(f"   Source: {art.get('source')}")
        print(f"   Overall Score: {score.get('overall_score')}/10")
        print(f"   Reason: {score.get('reason')}".encode('ascii', 'replace').decode('ascii'))
        print(f"   Scores -> Brand: {score.get('brand_relevance')} | Audience: {score.get('audience_relevance')} | Virality: {score.get('virality_potential')} | Opp: {score.get('content_opportunity')}")
    except Exception:
        pass

