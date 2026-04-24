import json
import logging
import os
import time

import google.generativeai as genai
from google.generativeai.types import generation_types

import config
from pipeline.key_manager import gemini_keys
from pipeline.tone_extractor import load_tone_profile

logger = logging.getLogger(__name__)

# Load the tone profile globally (fetches from YouTube on first run)
_TONE_PROFILE = load_tone_profile()

# Spoken-script platforms that get the humanizer pass
_SPOKEN_PLATFORMS = {"youtube_script", "youtube_shorts", "instagram_reel"}

# Per-platform temperature: higher = more creative/human, lower = more precise
PLATFORM_TEMPERATURE = {
    "youtube_script":      0.85,
    "youtube_shorts":      0.85,
    "instagram_reel":      0.85,
    "instagram_carousel":  0.6,
    "instagram_post":      0.6,
    "linkedin_post":       0.5,
    "twitter_thread":      0.65,
    "blog_article":        0.5,
}

def _build_tone_injection(tone_profile: dict, platform: str = "") -> str:
    """
    Converts the tone profile dict into a formatted string
    that gets injected into every platform prompt.
    Platform parameter enables voice modulation per channel.
    """
    # Platform-specific voice intensity
    casual_platforms = {"youtube_script", "youtube_shorts", "instagram_reel"}
    formal_platforms = {"linkedin_post", "blog_article"}
    
    if platform in casual_platforms:
        voice_mode = "CASUAL — Write exactly like Simran talks on YouTube. Use natural speech imperfections: 'right?', 'na?', self-corrections, thinking-out-loud moments. This should sound like someone SPEAKING, not writing."
    elif platform in formal_platforms:
        voice_mode = "PROFESSIONAL — Keep Simran's warmth and data-grounding but use clean, professional English. No fillers. No Hinglish. Still empathetic, still conversational — just polished."
    else:
        voice_mode = "SOCIAL — Punchy, direct, scroll-stopping. Use Simran's short-short-long rhythm. Occasional Hinglish okay. Every line must earn its place."

    return f"""
=== SIMRAN'S VOICE — MANDATORY RULES ===

YOU ARE SIMRAN JAKHAR. You are 26. IIT Delhi 2018-22 graduate. You co-founded EpiCred
because you saw your own friends struggle with ₹30 lakh loans they didn't understand.
You talk like a smart didi who happens to know finance. You are NOT a content creator,
NOT a marketer, NOT an AI. You are a real person explaining things to a younger sibling.

VOICE MODE FOR THIS PLATFORM: {voice_mode}

TONE: {', '.join(tone_profile.get('tone_adjectives', []))}

SENTENCE RHYTHM: {tone_profile.get('sentence_rhythm', '')}
- Short sentences: ~{tone_profile.get('average_short_sentence_words', 8)} words
- Long sentences: ~{tone_profile.get('average_long_sentence_words', 22)} words
- Always alternate: short. short. longer explanation. short punchline.

HOW SIMRAN OPENS (use one of these structures, adapt to topic):
{chr(10).join(['- ' + p for p in tone_profile.get('hook_patterns', [])])}

TRANSITION PHRASES (use 2-3 of these per piece):
{chr(10).join(['- ' + p for p in tone_profile.get('transition_phrases', [])])}

HOW TO FRAME DATA (CRITICAL — never drop a number without context):
{tone_profile.get('data_framing_style', '')}

RHETORICAL QUESTIONS SIMRAN USES:
{chr(10).join(['- ' + q for q in tone_profile.get('rhetorical_questions', [])])}

STORYTELLING PATTERNS:
{chr(10).join(['- ' + s for s in tone_profile.get('storytelling_patterns', [])])}

CTA STRUCTURE (never aggressive, always empathetic):
{tone_profile.get('cta_pattern', '')}

EMPATHY PHRASES (use when addressing student anxiety):
{chr(10).join(['- ' + p for p in tone_profile.get('empathy_phrases', [])])}

HINGLISH — natural usage only:
{', '.join(tone_profile.get('hinglish_words', []))}

NATURAL FILLERS (for spoken scripts — sprinkle 1-2 per piece):
{', '.join(tone_profile.get('filler_words_natural', []))}

AUDIENCE ADDRESS: {tone_profile.get('audience_address', '')}

CLOSING PATTERNS:
{chr(10).join(['- ' + c for c in tone_profile.get('closing_patterns', [])])}

BANNED WORDS — NEVER use these (instant fail if any appear):
{', '.join(tone_profile.get('banned_words', []))}

REAL VOICE EXAMPLES — mimic the rhythm, NOT the content:
{chr(10).join([f'"' + s + '"' for s in tone_profile.get('three_example_sentences', [])])}

=== ANTI-AI QUALITY CHECK ===
Before returning, re-read your output and ask:
1. Does this sound like a PERSON talking, or a press release?
2. Would Simran actually say this sentence out loud?
3. Are there any words from the BANNED list?
4. Did I start with the student's ANXIETY, not a generic greeting?
If ANY answer is wrong, rewrite that part.
=== END VOICE RULES ===
"""

def _load_prompt(platform: str) -> str:
    """Loads the prompt template for the specific platform."""
    filename = f"{platform}.txt"
    filepath = os.path.join(config.BASE_DIR, "prompts", filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Prompt template not found: {filepath}")
    
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def _generate_long_youtube_script(article: dict, outline_prompt: str, max_attempts: int, social: dict) -> dict | None:
    """Helper to generate a multi-step 7-8 minute long YouTube script."""
    logger.info("Starting multi-step YouTube long-script generation...")
    # 1. Generate the outline
    outline = None
    success = False
    attempts = 0
    while not success and attempts < max_attempts:
        key = gemini_keys.current()
        if not key:
            break
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config={"response_mime_type": "application/json"}
        )
        try:
            response = model.generate_content(outline_prompt)
            content = response.text
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            outline = json.loads(content)
            success = True
        except Exception as e:
            attempts += 1
            if gemini_keys.on_error(e):
                logger.info("Gemini (youtube outline): rotated key, retrying...")
            else:
                break
                
    if not outline or "outline_sections" not in outline:
        logger.error("Failed to generate YouTube outline.")
        return None
        
    logger.info(f"Successfully generated YouTube outline with {len(outline.get('outline_sections', []))} sections.")
    
    # 2. Iterate and expand sections
    full_script_parts = []
    try:
        section_prompt_template = _load_prompt("youtube_script_section")
    except Exception as e:
        logger.error(f"Failed to load youtube_script_section prompt: {e}")
        return None
        
    for section in outline.get("outline_sections", []):
        sec_name = section.get("section_name", "")
        sec_topics = ", ".join(section.get("core_topics_to_cover", []))
        sec_human = section.get("human_touch_directive", "")
        
        prompt = section_prompt_template.replace("[TITLE]", str(article.get("title", ""))) \
                        .replace("[LENDER_DATA]", str(article.get("lender_data") or "N/A")) \
                        .replace("[NUMBEO_DATA]", str(article.get("numbeo_data") or "N/A")) \
                        .replace("[SECTION_NAME]", str(sec_name)) \
                        .replace("[SECTION_TOPICS]", str(sec_topics)) \
                        .replace("[HUMAN_TOUCH]", str(sec_human)) \
                        .replace("[PRESENTER_NAME]", str(config.PRESENTER_NAME))
                        
        success = False
        attempts = 0
        section_script = ""
        while not success and attempts < max_attempts:
            key = gemini_keys.current()
            if not key:
                break
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                generation_config={"response_mime_type": "application/json"}
            )
            try:
                response = model.generate_content(prompt)
                content = response.text
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                sec_data = json.loads(content)
                section_script = sec_data.get("section_script", "")
                success = True
                
                time.sleep(1) # Pacing and rotation visibility
            except Exception as e:
                attempts += 1
                if gemini_keys.on_error(e):
                    logger.info(f"Gemini (youtube section '{sec_name}'): rotated key, retrying...")
                else:
                    break
                    
        if section_script:
            full_script_parts.append(f"--- {sec_name.upper()} ---\n{section_script}\n")
        else:
            full_script_parts.append(f"--- {sec_name.upper()} ---\n[Failed to generate section]\n")
            
    # Combine everything
    final_output = {
        "video_title": outline.get("video_title", ""),
        "thumbnail_text": outline.get("thumbnail_text", ""),
        "presenter_intro": outline.get("presenter_intro", ""),
        "hook": outline.get("hook", ""),
        "full_script": "\n".join(full_script_parts),
        "cta_block": f"CTA: If you want a lender strategy based on your exact profile—not guesswork—reach out to EpiCred.\n\nWebsite: {social.get('website', '')}\nWhatsApp: {social.get('whatsapp', '')}",
        "partner_lenders_featured": outline.get("partner_lenders_featured", []),
        "myth_busted": outline.get("myth_busted", ""),
        "description": outline.get("description", ""),
        "tags": outline.get("tags", []),
        "estimated_duration_minutes": 3.5
    }
    
    logger.info("Successfully assembled multi-step 3.5 min YouTube script.")
    return final_output

def generate_platform_content(article: dict, platform: str) -> dict | None:
    """
    Calls Gemini to generate content for a specific platform.
    Returns a structured dictionary matching the platform's JSON schema, or None on failure.
    """
    if not gemini_keys or not gemini_keys.available:
        logger.error("Gemini: no valid API keys configured for Content Generator.")
        return None

    try:
        prompt_template = _load_prompt(platform)
    except Exception as e:
        logger.error(f"Failed to load prompt for {platform}: {e}")
        return None

    summary = article.get("summary", "")
    if article.get("numbeo_data"):
        summary += f"\n\n[MANDATORY CONTEXT: Cost of Living for this City: {article['numbeo_data']} - Cite these specific costs to build trust.]"
    if article.get("lender_data"):
        summary += f"\n\n[CRITICAL INSTRUCTION: You MUST mention the following financial options/schemes in this specific post to help the user: {article['lender_data']}. Weave them naturally into the dialogue or call-to-action.]"

    # Build social links for branded footer
    social = config.EPICRED_SOCIAL_LINKS

    prompt = prompt_template.replace("[TITLE]", str(article.get("title", ""))) \
                            .replace("[SUMMARY]", str(summary)) \
                            .replace("[SOURCE]", str(article.get("source", ""))) \
                            .replace("[LENDER_DATA]", str(article.get("lender_data") or "N/A")) \
                            .replace("[NUMBEO_DATA]", str(article.get("numbeo_data") or "N/A")) \
                            .replace("[PRESENTER_NAME]", str(config.PRESENTER_NAME)) \
                            .replace("[WEBSITE_LINK]", str(social.get("website", ""))) \
                            .replace("[WHATSAPP_LINK]", str(social.get("whatsapp", ""))) \
                            .replace("[LINKEDIN_LINK]", str(social.get("linkedin", ""))) \
                            .replace("[INSTAGRAM_LINK]", str(social.get("instagram", ""))) \
                            .replace("[FACEBOOK_LINK]", str(social.get("facebook", ""))) \
                            .replace("[PRESENTER_LINKEDIN]", str(social.get("presenter_linkedin", ""))) \
                            .replace("[TONE_PROFILE]", _build_tone_injection(_TONE_PROFILE, platform))

    max_attempts = gemini_keys._keys.__len__() if gemini_keys else 1
    
    # Intercept for multi-step YouTube long script
    if platform == "youtube_script":
        return _generate_long_youtube_script(article, prompt, max_attempts, social)

    success = False
    attempts = 0

    while not success and attempts < max_attempts:
        key = gemini_keys.current()
        if not key:
            break

        genai.configure(api_key=key)
        
        # We explicitly request JSON output from the model
        temp = PLATFORM_TEMPERATURE.get(platform, 0.7)
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config={"response_mime_type": "application/json", "temperature": temp}
        )

        try:
            response = model.generate_content(prompt)
            content = response.text
            
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            
            result = json.loads(content)
            logger.info(f"Successfully generated {platform} content for '{article.get('title')[:30]}...'")
            
            # Humanizer pass for spoken scripts only
            if platform in _SPOKEN_PLATFORMS:
                result = _humanize_pass(result, platform)
            
            return result
            
        except generation_types.StopCandidateException as e:
             logger.warning(f"Gemini stopped generation unexpectedly for {platform}: {e}")
             return None
        except json.JSONDecodeError as e:
            logger.error(f"Gemini returned non-JSON for {platform}: {e} | Raw: {content[:200] if 'content' in dir() else 'N/A'}")
            return None
        except Exception as e:
            attempts += 1
            logger.warning(f"Gemini ({platform}) exception [{type(e).__name__}]: {e}")
            if gemini_keys.on_error(e):
                logger.info(f"Gemini ({platform}): rotated key, retrying...")
            else:
                logger.error(f"Gemini ({platform}): non-quota error, giving up: {e}")
                break
                
    return None


def _humanize_pass(result: dict, platform: str) -> dict:
    """
    Second-pass rewriter for spoken scripts.
    Catches AI-sounding phrases and rewrites them in Simran's voice.
    Only runs for youtube_script, youtube_shorts, instagram_reel.
    """
    # Identify the text field to humanize
    text_fields = {
        "youtube_shorts": ["speech"],
        "instagram_reel": ["speech"],
        "youtube_script": ["full_script", "hook"],
    }
    fields = text_fields.get(platform, [])
    texts_to_fix = {}
    for f in fields:
        if f in result and isinstance(result[f], str) and len(result[f]) > 30:
            texts_to_fix[f] = result[f]
    
    if not texts_to_fix:
        return result
    
    banned = _TONE_PROFILE.get('banned_words', [])
    banned_str = ', '.join(banned)
    
    prompt = f"""You are a script editor for Simran Jakhar (EpiCred YouTube channel).
Your ONLY job is to rewrite AI-sounding phrases into Simran's natural voice.

RULES:
- Replace any corporate/AI buzzwords with simple, conversational alternatives
- Add 1-2 natural speech fillers like "right?", "na?", "honestly," where they fit
- Break any sentence longer than 25 words into shorter beats
- Keep the EXACT same meaning and data — only change HOW it's said
- BANNED WORDS (if you find any, replace immediately): {banned_str}
- The output must sound like someone TALKING to a friend, not writing an essay

Here are the texts to humanize (return as JSON with same keys):
{json.dumps(texts_to_fix, ensure_ascii=False)}

Return ONLY valid JSON with the same keys, humanized values. No explanation."""
    
    try:
        key = gemini_keys.current()
        if not key:
            logger.warning("Humanizer: no API key available, skipping pass.")
            return result
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config={"response_mime_type": "application/json", "temperature": 0.9}
        )
        response = model.generate_content(prompt)
        content = response.text
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        
        humanized = json.loads(content)
        for f, val in humanized.items():
            if f in result and isinstance(val, str):
                result[f] = val
        logger.info(f"Humanizer pass completed for {platform} ({len(humanized)} fields rewritten).")
    except Exception as e:
        logger.warning(f"Humanizer pass failed for {platform}: {e}. Using original output.")
    
    return result
