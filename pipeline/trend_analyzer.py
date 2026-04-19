import json
import logging
import os
import time
from pipeline import news_fetcher as _nf

import google.generativeai as genai
from google.generativeai.types import generation_types

import config
from pipeline.key_manager import gemini_keys

logger = logging.getLogger(__name__)

def _load_prompt() -> str:
    prompt_path = os.path.join(config.BASE_DIR, "prompts", "trend_score.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def _score_article(article: dict, prompt_template: str) -> dict | None:
    """Uses Gemini to score a single article. Returns the extracted JSON or None on failure."""
    if not gemini_keys or not gemini_keys.available:
        logger.error("Gemini: no valid API keys configured.")
        return None

    prompt = prompt_template.replace("[TITLE]", article.get("title", "")).replace("[SUMMARY]", article.get("summary", "")).replace("[SOURCE]", article.get("source", ""))

    success = False
    attempts = 0
    max_attempts = gemini_keys._keys.__len__() if gemini_keys else 1

    while not success and attempts < max_attempts:
        key = gemini_keys.current()
        if not key:
            break

        genai.configure(api_key=key)
        
        # We explicitly request JSON output if the model supports it
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config={"response_mime_type": "application/json"}
        )

        try:
            response = model.generate_content(prompt)
            # Parse the response text as JSON
            content = response.text
            # Sometimes models return ```json ... ``` blocks
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            
            result = json.loads(content)
            return result
            
        except generation_types.StopCandidateException as e:
             logger.warning(f"Gemini stopped generation unexpectedly: {e}")
             return None
        except Exception as e:
            attempts += 1
            if gemini_keys.on_error(e):
                logger.info("Gemini: rotated key, retrying...")
            else:
                logger.error(f"Gemini error scoring article: {e}")
                break
                
    return None

import threading

def _bg_scoring_thread(articles_to_score: list, prompt_template: str, all_articles: list):
    """Worker thread that grades articles in the background and saves to cache incrementally."""
    logger.info(f"Background thread started: {len(articles_to_score)} articles remaining.")
    
    for article in articles_to_score:
        score_data = _score_article(article, prompt_template)
        if score_data:
            article["score"] = score_data
        else:
            article["score"] = {"overall_score": 0, "reason": "background_scoring_failed"}
        
        # Incremental save after every batch of 5 to minimize data loss if server restarts
        # Using save_cache (which has the thread lock we added earlier)
        _nf.save_cache(all_articles)
        
    logger.info("Background scoring complete.")

def analyze_and_filter_articles(articles: list[dict], foreground_limit: int = 3) -> list[dict]:
    """
    Foreground: Scores articles until 'foreground_limit' high-value articles are found.
    Background: Spawns a thread to finish the rest.
    Returns: The list of articles found so far.
    """
    prompt_template = _load_prompt()
    recommended = []
    unscored_indices = []

    # ── Phase 1: Check existing scores first ──
    for idx, article in enumerate(articles):
        if article.get("score") is not None:
            if (article["score"].get("overall_score") or 0) >= config.TREND_SCORE_THRESHOLD:
                recommended.append(article)
        else:
            unscored_indices.append(idx)

    # ── Phase 2: Foreground Scoring (Lazy Load) ──
    # If we already have enough from cache, don't block the user at all
    if len(recommended) < foreground_limit and unscored_indices:
        logger.info(f"Foreground scoring aiming for {foreground_limit} articles...")
        idx_pointer = 0
        while len(recommended) < foreground_limit and idx_pointer < len(unscored_indices):
            actual_idx = unscored_indices[idx_pointer]
            article = articles[actual_idx]
            
            logger.info(f"Force scoring [Foreground] {idx_pointer+1}: {article.get('title', '')[:40]}...")
            score_data = _score_article(article, prompt_template)
            
            if score_data:
                article["score"] = score_data
                if (score_data.get("overall_score") or 0) >= config.TREND_SCORE_THRESHOLD:
                    recommended.append(article)
            else:
                article["score"] = {"overall_score": 0, "reason": "scoring_failed"}
            
            idx_pointer += 1
        
        # Safe save for the foreground ones
        _nf.save_cache(articles)

    # ── Phase 3: Background Thread ──
    # Collect indices that are still unscored
    remaining_to_score = [articles[i] for i in unscored_indices if articles[i].get("score") is None]
    if remaining_to_score:
        bg_thread = threading.Thread(
            target=_bg_scoring_thread, 
            args=(remaining_to_score, prompt_template, articles),
            daemon=True
        )
        bg_thread.start()
        logger.info(f"Spawned background thread for {len(remaining_to_score)} remaining articles.")

    # ── Phase 4: Strategic Sorting (P1 > P2 > P3 > P4) ──
    # Sort criteria: 
    # 1. Priority (P1 > P2 > P3 > P4 > SKIP)
    # 2. Overall Score (10 > 0)
    
    priority_map = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "SKIP": 99}
    
    def get_sort_key(art):
        score = art.get("score") or {}
        prio = score.get("priority", "SKIP")
        prio_val = priority_map.get(prio, 99)
        score_val = score.get("overall_score") or 0
        return (prio_val, -score_val) # Ascending for prio_val, descending for score_val

    recommended.sort(key=get_sort_key)
    return recommended
