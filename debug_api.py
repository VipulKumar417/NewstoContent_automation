import config
import requests
import feedparser

print("GNEWS KEY:", config.GNEWS_API_KEY)
# Test GNews
base_url = "https://gnews.io/api/v4/search"
params = {"apikey": config.GNEWS_API_KEY, "q": "education loan india", "lang": "en", "country": "in", "max": 10}
r = requests.get(base_url, params=params)
print("GNews Status:", r.status_code)
print("GNews Body:", r.text[:200])

# Test NewsData
nd_key = config.NEWSDATA_API_KEY
print("NEWSDATA KEY:", nd_key)
nd_url = "https://newsdata.io/api/1/news"
nd_params = {"apikey": nd_key, "q": "education loan india", "country": "in", "language": "en", "category": "education,business"}
r = requests.get(nd_url, params=nd_params)
print("NewsData Status:", r.status_code)
print("NewsData Body:", r.text[:200])

# Test RSS
fee = feedparser.parse("https://www.shiksha.com/rss/news.xml")
print("RSS Feed Entries:", len(fee.entries))
if getattr(fee, "bozo_exception", None):
    print("RSS Exception:", fee.bozo_exception)
