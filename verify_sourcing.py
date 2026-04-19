import json
import logging
from pipeline.trend_analyzer import analyze_and_filter_articles
from pipeline.content_generator import generate_platform_content

logging.basicConfig(level=logging.INFO)

def main():
    with open('storage/news_cache.json', 'r', encoding='utf-8') as f:
        cache = json.load(f)
    
    print("\n--- ANALYZING ARTICLES ---")
    recommended = analyze_and_filter_articles(cache, foreground_limit=3)
    
    print("\n--- TOP 5 STRATEGIC RESULTS ---")
    for a in recommended[:5]:
        score = a.get('score', {})
        print(f"[{score.get('priority', 'N/A')}] Score: {score.get('overall_score')} | {a.get('title')}")
    
    if recommended:
        top_art = recommended[0]
        print(f"\n--- GENERATING BLOG ARTICLE FOR: {top_art.get('title')} ---")
        blog = generate_platform_content(top_art, 'blog_article')
        if blog:
            print("\nBlog Title:", blog.get('h1_title'))
            print("Meta Description:", blog.get('meta_description'))
            print("Word Count:", blog.get('word_count'))
            print("\nArticle HTML (Snippet):", blog.get('article_content_html')[:500] + "...")
        else:
            print("Failed to generate blog article.")

if __name__ == "__main__":
    main()
