import json
with open('storage/news_cache.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for a in data:
    a['score'] = None
with open('storage/news_cache.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
