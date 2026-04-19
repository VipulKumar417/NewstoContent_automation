import json
with open('storage/news_cache.json', 'r', encoding='utf-8') as f:
    for a in json.load(f):
        if 'score' in a and a['score']:
            s = a['score']
            print("\n" + "="*40)
            print(f"Title: {a['title']}")
            print(f"Total Score: {s.get('overall_score')}/10")
            print(f"Reason: {s.get('reason')}")
            print(f"Brand: {s.get('brand_relevance')} | Audience: {s.get('audience_relevance')} | Virality: {s.get('virality_potential')} | Opportunity: {s.get('content_opportunity')}")
