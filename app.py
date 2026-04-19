import logging
from flask import Flask, render_template, jsonify, request

from pipeline.news_fetcher import fetch_all_news, load_cache, is_cache_fresh
from pipeline.trend_analyzer import analyze_and_filter_articles
from pipeline.repurposer import repurpose_article
from pipeline.google_integration import get_google_services, save_to_drive, create_google_doc, schedule_calendar_event

# Configure simple logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

app = Flask(__name__, template_folder='dashboard/templates', static_folder='dashboard/static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/news', methods=['GET'])
def get_news():
    force = request.args.get('force', 'false').lower() == 'true'
    
    # Only hit the external APIs when the cache is genuinely stale (>24 h)
    # or the user explicitly clicks "Force Refresh". This preserves daily quota.
    if force or not is_cache_fresh():
        articles = fetch_all_news(force=True)
    else:
        # Load raw articles (may include previously-scored ones from cache)
        articles = load_cache()
    
    if not articles:
        return jsonify({"articles": [], "warning": "No news articles available yet. Try again later."})
    
    # Score unscored articles via Gemini; scores are persisted back to cache
    # so subsequent /api/news calls are instant and quota-free.
    scored = analyze_and_filter_articles(articles)
    
    # Safety net: if the scorer returned nothing (all failed / all below threshold),
    # send back the raw cached articles so the dashboard is never empty.
    if not scored:
        logging.warning("Scorer returned 0 articles — sending raw cache as fallback.")
        scored = sorted(
            articles,
            key=lambda a: a.get("published_at") or "",
            reverse=True
        )
        
    return jsonify({"articles": scored})

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    article = data.get('article', {})
    
    if not article:
         return jsonify({"error": "No article provided"}), 400
         
    # Calls Phase 3 recursive AI generation array
    bundle = repurpose_article(article)
    return jsonify({"bundle": bundle, "article": article})

@app.route('/api/save', methods=['POST'])
def save():
    data = request.json
    bundle = data.get('bundle', {})
    article = data.get('article', {})
    
    title = article.get('title', 'Unknown Campaign')
    
    if not bundle:
        return jsonify({"error": "No generated content provided"}), 400
        
    drive_service, docs_service, calendar_service = get_google_services()
    if not drive_service:
        return jsonify({"error": "Google Workspace authentication dropped"}), 500
        
    # Execute Phase 4 operations sequentially
    json_id = save_to_drive(drive_service, title, bundle)
    doc_id = create_google_doc(drive_service, docs_service, title, bundle)
    
    calendar_events = {}
    for platform in bundle.keys():
        # Will only schedule if platform successfully generated and has rules setup
        link = schedule_calendar_event(calendar_service, title, doc_id, platform)
        if link:
            calendar_events[platform] = link
            
    return jsonify({
        "success": True, 
        "drive_json_id": json_id, 
        "drive_doc_id": doc_id, 
        "calendar_links": calendar_events
    })

@app.route('/api/reset-keys', methods=['POST'])
def reset_keys():
    """Manually reset all exhausted API key states without restarting the server."""
    from pipeline.key_manager import gemini_keys, newsdata_keys
    if gemini_keys:
        gemini_keys.reset()
    if newsdata_keys:
        newsdata_keys.reset()
    logging.info("All API key exhaustion states have been reset.")
    return jsonify({"success": True, "message": "All API key exhaustion states reset."})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
