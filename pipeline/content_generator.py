import json
import logging
import os
import time

import google.generativeai as genai
from google.generativeai.types import generation_types

import config
from pipeline.key_manager import gemini_keys

logger = logging.getLogger(__name__)

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
        "estimated_duration_minutes": 7.5
    }
    
    logger.info("Successfully assembled multi-step 7-8 min YouTube script.")
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
                            .replace("[PRESENTER_LINKEDIN]", str(social.get("presenter_linkedin", "")))

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
            
            result = json.loads(content)
            logger.info(f"Successfully generated {platform} content for '{article.get('title')[:30]}...'")
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
