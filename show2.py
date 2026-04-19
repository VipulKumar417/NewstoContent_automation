import json
with open('show_log.txt', 'w', encoding='utf-8') as out:
    with open('storage/news_cache.json', 'r', encoding='utf-8') as f:
        for a in json.load(f):
            if 'score' in a and a['score']:
                s = a['score']
                out.write("\n" + "="*40 + "\n")
                out.write(f"Title: {a['title']}\n")
                out.write(f"Total Score: {s.get('overall_score')}/10\n")
                out.write(f"Reason: {s.get('reason')}\n")
                out.write(f"Brand: {s.get('brand_relevance')} | Audience: {s.get('audience_relevance')} | Virality: {s.get('virality_potential')} | Opportunity: {s.get('content_opportunity')}\n")
