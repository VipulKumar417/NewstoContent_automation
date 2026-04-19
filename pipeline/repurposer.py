import logging
import time

from pipeline.content_generator import generate_platform_content
from pipeline.numbeo_integration import fetch_cost_of_living
import config

logger = logging.getLogger(__name__)

PLATFORMS = [
    "blog_article",
    "instagram_reel",
    "instagram_carousel",
    "instagram_post",
    "linkedin_post",
    "twitter_thread",
    "youtube_shorts",
    "youtube_script"
]

def repurpose_article(article: dict) -> dict:
    """
    Orchestrates the generation of all 6 platform formats for a single article.
    Returns a master dictionary containing all the generated formats under 'content'.
    """
    logger.info(f"\n--- Repurposing Article: {article.get('title', '')[:40]}... ---")
    
    # ── Inject Numbeo Cost of Living Data if applicable ──
    score_data = article.get("score", {})
    target_city = score_data.get("target_city")
    if target_city:
        logger.info(f"Target city detected: {target_city}. Fetching Numbeo data...")
        numbeo_info = fetch_cost_of_living(target_city)
        if numbeo_info:
            # Add a social-ready comparison context
            article["numbeo_data"] = f"🌍 GLOBAL INTELLIGENCE: {numbeo_info}. (Use this to craft a 'Money-Saving' or 'Budgeting' angle for the student audience.)"
            
    # ── Inject Specific Lender/Scheme Data (Direct + Semantic) ──
    text_to_scan = (article.get("title", "") + " " + article.get("summary", "")).upper()
    mentioned_entities = []
    
    # Semantic Mapping: Keywords that anchor specific schemes
    keyword_map = {
        # State-specific triggers
        "BIHAR":        ["Bihar State Co-op Bank"],
        "DELHI":        ["DSFDC Delhi Loan", "Delhi Edu Guarantee Scheme"],
        "MAHARASHTRA":  ["Rajarshi Shahu Scholarship", "Maharashtra Post-Matric Scholarship"],
        "TELANGANA":    ["Telangana Co-op Apex Bank"],
        "HIMACHAL":     ["HPSCB"],
        # Category triggers
        "SC/ST":        ["Top Class Education Scheme", "Maharashtra Post-Matric Scholarship"],
        "OBC":          ["Maharashtra Post-Matric Scholarship", "NBCFDC"],
        "BACKWARD":     ["NBCFDC"],
        "SUBSIDY":      ["CSIS", "PM Vidyalaxmi"],
        "INTEREST WAIVER":["CSIS"],
        "MORATORIUM":   ["CSIS", "PM Vidyalaxmi"],
        "COLLATERAL":   ["PM Vidyalaxmi", "SBI"],
        # Study level triggers
        "ENGINEERING":  ["AICTE Scholarships"],
        "MEDICAL":      ["PM Vidyalaxmi", "Central Sector Scheme"],
        "TIER 2":       ["PM Vidyalaxmi", "NMMS"],
        "TIER 3":       ["PM Vidyalaxmi", "NMMS"],
        # Country triggers (no-cosigner lenders)
        "USA":          ["Prodigy Finance", "Leap Finance"],
        "UK":           ["Prodigy Finance", "HDFC Credila"],
        "CANADA":       ["Leap Finance", "HDFC Credila"],
        "GERMANY":      ["Prodigy Finance", "Avanse"],
        "AUSTRALIA":    ["Auxilo", "Avanse"],
    }

    # 1. Direct name matching
    for entity_name, data in config.TRACKED_ENTITIES.items():
        if entity_name.upper() in text_to_scan:
            mentioned_entities.append(f"{entity_name}: {data['benefit']} ({data['rate']})")
    
    # 2. Semantic matching (injects relevant schemes by keyword)
    for kw, target_list in keyword_map.items():
        if kw in text_to_scan:
            for target_name in target_list:
                if target_name in config.TRACKED_ENTITIES:
                    data = config.TRACKED_ENTITIES[target_name]
                    # Don't duplicate if already found by direct match
                    if not any(target_name in me for me in mentioned_entities):
                        mentioned_entities.append(f"{target_name} [RECOMMENDED]: {data['benefit']} ({data['rate']})")
    
    if mentioned_entities:
        logger.info(f"Target entities/schemes detected: {len(mentioned_entities)}. Attaching precise stats.")
        article["lender_data"] = " | ".join(mentioned_entities)
            
    content_bundle = {}
    
    for platform in PLATFORMS:
        logger.info(f" -> Generating {platform}")
        # Keys are now load-balanced round-robin, so we can go fast again
        time.sleep(2)
        
        result = generate_platform_content(article, platform)
        if result:
            content_bundle[platform] = result
        else:
            logger.warning(f"Failed to generate content for {platform}")
            content_bundle[platform] = None
            
    logger.info(f"--- Finished repurposing. Generated {len([v for v in content_bundle.values() if v])}/{len(PLATFORMS)} formats ---\n")
    return content_bundle
