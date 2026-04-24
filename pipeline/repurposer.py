import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from pipeline.content_generator import generate_platform_content
from pipeline.numbeo_integration import fetch_cost_of_living
import config

logger = logging.getLogger(__name__)

# ── Platform Generation Waves ────────────────────────────────────────────────
# With 33 Gemini keys, we can fire multiple platforms in parallel.
# Waves ensure the highest-value content generates first, spreading API load.
#
#   Wave 1 (flagship):  Long-form, data-heavy → needs most API calls
#   Wave 2 (video):     Short-form video scripts → medium API load
#   Wave 3 (text):      Static posts & threads → lightest API load
#
GENERATION_WAVES = [
    # Wave 1 — Flagship content (these take longest, start first)
    ["youtube_script", "blog_article", "linkedin_post"],
    # Wave 2 — Video scripts (shorter, but still spoken-word)
    ["instagram_reel", "youtube_shorts", "instagram_carousel"],
    # Wave 3 — Quick text formats
    ["instagram_post", "twitter_thread"],
]


def _generate_single(article: dict, platform: str) -> tuple[str, dict | None]:
    """Worker function for thread pool: generates content for one platform."""
    try:
        result = generate_platform_content(article, platform)
        return (platform, result)
    except Exception as e:
        logger.error(f"Unhandled error generating {platform}: {e}")
        return (platform, None)


def repurpose_article(article: dict) -> dict:
    """
    Orchestrates the generation of all 8 platform formats for a single article.
    Uses wave-based parallel generation for speed:
      - Each wave fires its platforms concurrently via ThreadPoolExecutor
      - Waves run sequentially so flagship content finishes first
      - With 33 keys, each concurrent call gets its own key slot

    Returns a master dictionary containing all the generated formats.
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
    total_platforms = sum(len(w) for w in GENERATION_WAVES)

    for wave_num, wave_platforms in enumerate(GENERATION_WAVES, 1):
        logger.info(f"🚀 Wave {wave_num}/{len(GENERATION_WAVES)}: Launching {wave_platforms} in parallel...")

        # Each wave gets its own thread pool — platforms within a wave run concurrently
        with ThreadPoolExecutor(max_workers=len(wave_platforms)) as executor:
            futures = {
                executor.submit(_generate_single, article, platform): platform
                for platform in wave_platforms
            }

            for future in as_completed(futures):
                platform, result = future.result()
                if result:
                    content_bundle[platform] = result
                    logger.info(f"  ✅ {platform} — generated successfully")
                else:
                    logger.warning(f"  ❌ {platform} — failed to generate")
                    content_bundle[platform] = None

        # Brief pause between waves to let key cooldowns recover
        if wave_num < len(GENERATION_WAVES):
            time.sleep(1)

    success_count = len([v for v in content_bundle.values() if v])
    logger.info(f"--- Finished repurposing. Generated {success_count}/{total_platforms} formats ---\n")
    return content_bundle
