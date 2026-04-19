import config
import requests
import feedparser

with open("api_raw_log.txt", "w", encoding="utf-8") as f:
    f.write(f"GNEWS KEY: {config.GNEWS_API_KEY}\n")
    # Test GNews
    base_url = "https://gnews.io/api/v4/search"
    params = {"apikey": config.GNEWS_API_KEY, "q": "education loan", "lang": "en", "country": "in", "max": 10}
    r = requests.get(base_url, params=params)
    f.write(f"GNews Status: {r.status_code}\n")
    f.write(f"GNews Body: {r.text[:200]}\n")

    # Test NewsData
    nd_key = config.NEWSDATA_API_KEY
    f.write(f"NEWSDATA KEY: {nd_key}\n")
    nd_url = "https://newsdata.io/api/1/news"
    nd_params = {"apikey": nd_key, "q": "education loan", "country": "in", "language": "en", "category": "education,business"}
    r = requests.get(nd_url, params=nd_params)
    f.write(f"NewsData Status: {r.status_code}\n")
    f.write(f"NewsData Body: {r.text[:200]}\n")

    # Test RSS
    fee = feedparser.parse("https://www.shiksha.com/rss/news.xml")
    f.write(f"RSS Feed Entries Shiksha: {len(fee.entries)}\n")
    if getattr(fee, "bozo_exception", None):
         f.write(f"RSS Exception Shiksha: {fee.bozo_exception}\n")
    
    fee2 = feedparser.parse("https://www.thehindubusinessline.com/education/feeder/default.rss")
    f.write(f"RSS Feed Entries Hindu: {len(fee2.entries)}\n")
