"""
news_fetcher.py — News Ingestion Engine for EpiCred Content Automation

Fetches education/fintech news from:
  1. NewsData.io API (primary)   — up to 3 keys with auto-rotation
  2. GNews API (secondary)
  3. RSS feeds — Hindu Business Line, Economic Times, Shiksha (fallback)

Deduplicates by URL and saves to news_cache.json.
"""
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from hashlib import md5

import feedparser
import requests

import config
from pipeline.key_manager import newsdata_keys

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_article(title: str, source: str, url: str, summary: str, published_at: str) -> dict:
    """Return a normalised article dict."""
    return {
        "id": md5(url.encode()).hexdigest()[:12],
        "title": title.strip(),
        "source": source.strip(),
        "url": url.strip(),
        "summary": (summary or "").strip()[:600],
        "published_at": published_at,
        "fetched_at": _now_iso(),
        "score": None,  # filled later by trend_analyzer
    }


# ── Source 1: NewsData.io (with key rotation) ─────────────────────────────────

def fetch_newsdata() -> list[dict]:
    """
    Fetch articles from NewsData.io.
    Auto-rotates through configured NEWSDATA_API_KEY_* keys on quota errors.
    
    Keyword ordering: P1 partner entities first, then global trends, then generic SEO keywords.
    This ensures we max out our most-valuable queries first if quota is limited.
    """
    if not newsdata_keys or not newsdata_keys.available:
        logger.warning("NewsData.io: no valid API keys configured — skipping.")
        return []

    articles = []
    base_url = "https://newsdata.io/api/1/news"

    # Global lenders that need worldwide results (no country=in filter)
    GLOBAL_LENDERS = {
        "Prodigy Finance", "Leap Finance", "InCred Finance", "Avanse",
        "Auxilo", "HDFC Credila",
    }

    # P1 first (partner entities) → P3/P4 (global trends) → P2 (generic SEO keywords last)
    keywords_to_use = list(config.TRACKED_KEYWORDS) + config.GLOBAL_TRENDS_KEYWORDS + config.NEWS_KEYWORDS

    for keyword in keywords_to_use:
        if not newsdata_keys.available:
            logger.warning("NewsData.io: all keys exhausted during search.")
            break

        # Determine if this keyword should be India-only or global
        is_global_kw = any(lender.lower() in keyword.lower() for lender in GLOBAL_LENDERS) or \
                       any(kw in keyword for kw in config.GLOBAL_TRENDS_KEYWORDS)

        success = False
        attempts = 0
        max_attempts = len(newsdata_keys._keys) if newsdata_keys else 1

        while not success and attempts < max_attempts:
            key = newsdata_keys.current()
            if not key:
                break

            try:
                params = {
                    "apikey":   key,
                    "q":        keyword,          # No quotes — broader matching, more results
                    "language": "en",
                    "category": "business,education",  # Pre-filter irrelevant categories
                }
                # India-specific searches (banks, govt schemes, domestic policy)
                if not is_global_kw:
                    params["country"] = "in"

                resp = requests.get(base_url, params=params, timeout=15)

                if resp.status_code in (429, 402):
                    raise Exception(f"HTTP {resp.status_code} Quota Error")
                resp.raise_for_status()
                data = resp.json()

                # 10 per keyword (down from 20) — covers 2x more keywords per quota
                for item in (data.get("results") or [])[:10]:
                    title = item.get("title") or ""
                    url   = item.get("link") or ""
                    if not title or not url:
                        continue
                    articles.append(_make_article(
                        title        = title,
                        source       = item.get("source_id") or "newsdata.io",
                        url          = url,
                        summary      = item.get("description") or item.get("content") or "",
                        published_at = item.get("pubDate") or _now_iso(),
                    ))
                success = True
                time.sleep(1)  # Rate-limit safety

            except Exception as e:
                attempts += 1
                if newsdata_keys.on_error(e):
                    logger.info(f"NewsData.io: rotated key, retrying '{keyword}'…")
                else:
                    logger.error(f"NewsData.io: error for '{keyword}': {e}")
                    break

    logger.info(f"NewsData.io: fetched {len(articles)} articles | {newsdata_keys.status()}")
    return articles


# ── Source 2: GNews ───────────────────────────────────────────────────────────

def fetch_gnews() -> list[dict]:
    """Fetch articles from GNews API (free tier: ~10 req/day).
    
    Only runs short, broad queries to avoid 400 errors on the free tier.
    Queries > 50 chars are skipped automatically.
    """
    gnews_key = config.GNEWS_API_KEY
    if not gnews_key or gnews_key.startswith("your_"):
        logger.warning("GNews API key not configured — skipping.")
        return []

    articles = []
    base_url = "https://gnews.io/api/v4/search"

    # GNews free tier: only short, broad queries that reliably work
    GNEWS_KEYWORDS = [
        "India education loan 2026",
        "SBI education loan",
        "HDFC education loan",
        "ICICI education loan",
        "PM Vidyalaxmi scholarship",
        "study abroad loan India",
        "Indian student scholarship abroad",
    ]

    for keyword in GNEWS_KEYWORDS:
        # Skip long queries that GNews free tier rejects with 400
        if len(keyword) > 50:
            continue
        try:
            params = {
                "apikey": gnews_key,
                "q":      keyword,
                "lang":   "en",
                "max":    10,
            }
            resp = requests.get(base_url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for item in (data.get("articles") or []):
                title = item.get("title") or ""
                url   = item.get("url") or ""
                if not title or not url:
                    continue
                articles.append(_make_article(
                    title        = title,
                    source       = (item.get("source") or {}).get("name") or "gnews",
                    url          = url,
                    summary      = item.get("description") or item.get("content") or "",
                    published_at = item.get("publishedAt") or _now_iso(),
                ))
            time.sleep(1)
        except Exception as e:
            logger.error(f"GNews fetch error for '{keyword}': {e}")
            break  # Stop on error to conserve the daily quota

    logger.info(f"GNews: fetched {len(articles)} articles")
    return articles


# ── Source 3: RSS Feeds ───────────────────────────────────────────────────────

def fetch_rss() -> list[dict]:
    """Parse RSS feeds — no API key required, unlimited fallback."""
    articles = []

    for feed_url in config.RSS_FEEDS:
        try:
            # RSS feeds often block default python bots or hang indefinitely
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(feed_url, headers=headers, timeout=10)
            r.raise_for_status()
            
            feed = feedparser.parse(r.text)
            source_name = feed.feed.get("title") or feed_url

            for entry in feed.entries[:config.MAX_ARTICLES_PER_SOURCE]:
                title = entry.get("title") or ""
                url   = entry.get("link") or ""
                if not title or not url:
                    continue

                summary = entry.get("summary") or entry.get("description") or ""
                summary = re.sub(r"<[^>]+>", " ", summary).strip()

                published_at = _now_iso()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published_at = datetime(
                            *entry.published_parsed[:6], tzinfo=timezone.utc
                        ).isoformat()
                    except Exception:
                        pass

                articles.append(_make_article(
                    title       = title,
                    source      = source_name,
                    url         = url,
                    summary     = summary,
                    published_at= published_at,
                ))
        except Exception as e:
            logger.error(f"RSS fetch error for '{feed_url}': {e}")

    logger.info(f"RSS: fetched {len(articles)} articles")
    return articles


# ── Source 4: Google News RSS (FREE, UNLIMITED, no API key needed) ────────────

def fetch_google_news_rss() -> list[dict]:
    """
    Scrape Google News RSS for education loan specific queries.
    This is the critical fallback — free, unlimited, and always available.
    
    Google News RSS format: https://news.google.com/rss/search?q=QUERY&hl=en-IN&gl=IN
    """
    articles = []
    
    # These queries are hyper-specific to education loans — no generic news
    GOOGLE_NEWS_QUERIES = [
        "education loan India",
        "education loan interest rate",
        "education loan study abroad India",
        "scholarship Indian students 2026",
        "SBI education loan",
        "HDFC education loan",
        "ICICI education loan",
        "Tata Capital education loan",
        "PM Vidyalaxmi education loan",
        "education loan rate cut",
        "education loan collateral free India",
        "Auxilo Avanse education loan",
        "Prodigy Finance student loan",
    ]
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for query in GOOGLE_NEWS_QUERIES:
        try:
            encoded_q = requests.utils.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-IN&gl=IN&ceid=IN:en"
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            
            feed = feedparser.parse(r.text)
            
            for entry in feed.entries[:5]:  # Top 5 per query
                title = entry.get("title") or ""
                link  = entry.get("link") or ""
                if not title or not link:
                    continue
                
                summary = entry.get("summary") or entry.get("description") or ""
                summary = re.sub(r"<[^>]+>", " ", summary).strip()
                
                # Extract source from Google News title format: "Title - Source Name"
                source_name = "Google News"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    source_name = parts[1].strip()
                
                # Clean up title: remove pipes, excessive punctuation, leading junk
                title = _clean_title(title)
                
                published_at = _now_iso()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published_at = datetime(
                            *entry.published_parsed[:6], tzinfo=timezone.utc
                        ).isoformat()
                    except Exception:
                        pass
                
                articles.append(_make_article(
                    title        = title,
                    source       = source_name,
                    url          = link,
                    summary      = summary,
                    published_at = published_at,
                ))
            time.sleep(0.5)  # Be gentle
        except Exception as e:
            logger.error(f"Google News RSS error for '{query}': {e}")
    
    logger.info(f"Google News RSS: fetched {len(articles)} articles")
    return articles


# ── Deduplication & Caching ───────────────────────────────────────────────────

def _deduplicate(articles: list[dict]) -> list[dict]:
    """Deduplicate by URL first, then by title similarity (catches same story from diff sources)."""
    seen_urls = set()
    seen_title_tokens: list[set] = []
    unique = []

    for article in articles:
        url = article.get("url", "")
        if url and url in seen_urls:
            continue

        # Title similarity check — skip if >70% word overlap with an already-seen title
        title_words = set(re.sub(r'[^\w\s]', '', article.get("title", "").lower()).split())
        title_words.discard("")  # remove empty string
        is_dupe = False
        if title_words:
            for seen_tokens in seen_title_tokens:
                if seen_tokens and len(title_words & seen_tokens) / max(len(title_words), len(seen_tokens)) > 0.70:
                    is_dupe = True
                    break

        if not is_dupe:
            if url:
                seen_urls.add(url)
            seen_title_tokens.append(title_words)
            unique.append(article)

    return unique


import threading

cache_lock = threading.Lock()

def load_cache() -> list[dict]:
    os.makedirs(config.STORAGE_DIR, exist_ok=True)
    with cache_lock:
        if not os.path.exists(config.NEWS_CACHE_PATH):
            return []
        try:
            with open(config.NEWS_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load news cache: {e}")
            return []


def save_cache(articles: list[dict]) -> None:
    os.makedirs(config.STORAGE_DIR, exist_ok=True)
    with cache_lock:
        try:
            with open(config.NEWS_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(articles)} articles to cache")
        except Exception as e:
            logger.error(f"Failed to save news cache: {e}")


def is_cache_fresh() -> bool:
    if not os.path.exists(config.NEWS_CACHE_PATH):
        return False
    age_hours = (time.time() - os.path.getmtime(config.NEWS_CACHE_PATH)) / 3600
    return age_hours < config.NEWS_CACHE_HOURS


def _clean_title(title: str) -> str:
    """Clean up raw Google News / RSS titles for professional display."""
    # Remove pipe-separated junk: "UNSW | Scholarship Release | Real Title" → "Real Title"
    if "|" in title:
        parts = [p.strip() for p in title.split("|")]
        # Keep the longest segment (usually the actual headline)
        title = max(parts, key=len)
    
    # Remove leftover source attribution: "Title — The Wire" 
    for sep in [" — ", " – ", " | "]:
        if sep in title:
            title = title.split(sep)[0].strip()
    
    # Sentence-case cleanup: "THIS IS ALL CAPS" → skip it (too junky)
    # But keep normal titles
    title = title.strip()
    
    return title


def _filter_money_only(articles: list[dict]) -> list[dict]:
    """
    Three-layer pre-filter for EpiCred quality:
    Layer 1: Block low-quality / irrelevant sources
    Layer 2: Article MUST contain education/student signal
    Layer 3: Article MUST ALSO contain money/loan signal
    Layer 4: Article MUST be India-relevant (or mention a partner lender)
    """
    # ── Blocked sources: low-quality, off-topic, or foreign political sites ──
    BLOCKED_SOURCES = {
        "socialistparty", "socialist", "dailymail", "foxnews", "breitbart",
        "buzzfeed", "tmz", "tripura star", "bollywood", "filmibeat",
        "cricket", "sports", "ndtv sports", "espn",
    }
    
    # ── Layer 1: Education/student signal ──
    EDUCATION_SIGNALS = {
        "education loan", "student loan", "education finance",
        "student credit card", "study abroad", "higher education",
        "scholarship", "tuition", "student finance",
        # Partner lender names (always pass)
        "credila", "auxilo", "avanse", "prodigy finance", "leap finance",
        "incred", "propelld", "tata capital",
        # Specific govt schemes (always pass)
        "vidyalaxmi", "vidyalakshmi", "nsp", "csis", "nbcfdc",
        "mahadbt", "dsfdc", "nmms", "aicte",
    }
    
    # ── Layer 2: Money/finance signal ──
    MONEY_SIGNALS = {
        "loan", "loans", "interest rate", "rate cut", "rate hike",
        "emi", "moratorium", "collateral", "subsidy", "subvention",
        "scholarship", "grant", "stipend", "fellowship", "waiver",
        "disburs", "eligibility", "repayment", "mclr", "repo rate",
        "lending", "lender", "npa", "financing",
    }
    
    # ── Layer 3: India relevance signal ──
    INDIA_SIGNALS = {
        "india", "indian", "rupee", "inr", "lakh", "crore",
        "rbi", "sbi", "icici", "hdfc", "axis bank", "kotak",
        "bank of baroda", "punjab national", "union bank",
        "nsp", "vidyalaxmi", "vidyalakshmi", "aicte", "ugc",
        "iit", "nit", "aiims", "jee", "neet",
        "maharashtra", "karnataka", "delhi", "bihar", "tamil nadu",
        "credila", "auxilo", "avanse", "propelld", "tata capital",
        "pm vidyalaxmi", "central sector", "mahadbt",
    }
    
    # ── Reject: kill even if matched above ──
    REJECT_SIGNALS = {
        "gold loan", "home loan", "car loan", "personal loan",
        "credit card reward", "forex trading", "mutual fund",
        "stock market", "ipo", "share price", "sensex", "nifty",
        "cricket", "election result", "bollywood",
        # Foreign-only student loan systems
        "plan 2 student loan", "plan 5 student loan",  # UK repayment plans
        "student loan forgiveness",  # US-only
        "fafsa", "pell grant",  # US-only
        "slc", "student loans company",  # UK-only
    }

    filtered = []
    for article in articles:
        title = article.get("title", "")
        text = (title + " " + article.get("summary", "")).lower()
        source = article.get("source", "").lower()
        
        # Block low-quality sources
        if any(blocked in source for blocked in BLOCKED_SOURCES):
            continue
        
        # Hard reject
        if any(reject in text for reject in REJECT_SIGNALS):
            continue
        
        has_education = any(sig in text for sig in EDUCATION_SIGNALS)
        has_money = any(sig in text for sig in MONEY_SIGNALS)
        has_india = any(sig in text for sig in INDIA_SIGNALS)
        
        # Must have education + money + India relevance
        if has_education and has_money and has_india:
            filtered.append(article)

    dropped = len(articles) - len(filtered)
    if dropped:
        logger.info(f"Pre-filter: dropped {dropped} non-India-education-loan articles, kept {len(filtered)}")
    return filtered


# ── Main Entry Point ──────────────────────────────────────────────────────────

def fetch_all_news(force: bool = False) -> list[dict]:
    """
    Orchestrate all sources, deduplicate, persist, and return articles.

    Args:
        force: If True, bypass cache TTL and always fetch fresh news.
    """
    if not force and is_cache_fresh():
        logger.info("Cache is fresh — loading from disk")
        return load_cache()

    # Persistent Cache Logic: Load existing articles first so we never show an empty screen
    all_articles = load_cache()
    
    logger.info("Fetching fresh news from all sources…")
    all_articles.extend(fetch_newsdata())
    all_articles.extend(fetch_gnews())
    all_articles.extend(fetch_rss())
    all_articles.extend(fetch_google_news_rss())  # Free fallback — always works

    # Step 1: Kill non-money articles before they ever reach the scorer
    all_articles = _filter_money_only(all_articles)
    
    # Step 2: Deduplicate by URL + title similarity
    unique = _deduplicate(all_articles)
    
    unique.sort(key=lambda a: a.get("published_at") or "", reverse=True)
    unique = unique[:200]

    save_cache(unique)
    logger.info(f"Total unique articles in persistent cache: {len(unique)}")
    return unique
