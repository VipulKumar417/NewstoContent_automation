import sys
sys.path.append('.')
from pipeline.news_fetcher import fetch_newsdata, fetch_gnews, fetch_rss

print("Testing RSS...")
try:
    rss = fetch_rss()
    print("RSS:", len(rss))
except Exception as e:
    print("RSS error:", e)

print("Testing GNews...")
try:
    gn = fetch_gnews()
    print("GNews:", len(gn))
except Exception as e:
    print("GNews Error:", e)

print("Testing NewsData...")
try:
    nd = fetch_newsdata()
    print("NewsData:", len(nd))
except Exception as e:
    print("NewsData Error:", e)
