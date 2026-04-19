import sys
import os
import json
import logging

logging.basicConfig(filename='test_phase3.log', filemode='w', level=logging.INFO, format='%(levelname)s - %(message)s')

# Ensure the project root is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline.news_fetcher import load_cache
from pipeline.repurposer import repurpose_article

print("\n" + "="*60)
print("  EpiCred Phase 3 — Content Generator Test")
print("="*60)

articles = load_cache()
recommended = [a for a in articles if a.get("score") and a["score"].get("overall_score", 0) >= 7]

if not recommended:
    print("⚠ No recommended articles found. Ensure Phase 2 found high scoring articles.")
    sys.exit(1)

# Pick the top recommended article
target_article = recommended[0]

print(f"\n[ Targeting Article ]")
safe_title = target_article.get('title', '').encode('ascii', 'ignore').decode('ascii')
print(f"Title   : {safe_title}")
print(f"Score   : {target_article.get('score', {}).get('overall_score')}/10")

print("\n[ Running Engine ]")
# Orchestrate the 6 formats
generated_content = repurpose_article(target_article)

print("\n" + "="*60)
print("  ✅ GENERATION COMPLETE")
print("="*60)

# Save result to a test file so we can view it cleanly
with open("test_phase3_output.json", "w", encoding="utf-8") as f:
    json.dump(generated_content, f, indent=2, ensure_ascii=False)

print("\Saved extracted dictionary to test_phase3_output.json")
