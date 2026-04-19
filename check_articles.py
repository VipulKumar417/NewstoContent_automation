import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('storage/news_cache.json', encoding='utf-8') as f:
    data = json.load(f)

print(f'Total education-loan articles: {len(data)}')
print('=' * 90)
for i, a in enumerate(data, 1):
    title = a.get('title', 'No title')[:85]
    source = a.get('source', '?')[:22]
    print(f'{i:2d}. [{source:22s}] {title}')
print('=' * 90)
