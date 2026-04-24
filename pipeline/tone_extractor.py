import os
import json
import logging
from typing import List, Dict
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
from pipeline.key_manager import gemini_keys

logger = logging.getLogger(__name__)

# Hardcoded video IDs to sample Simran's voice consistently
VIDEO_IDS = [
    "j1CaIYC7VRU",  # SBI vs ICICI vs Credila vs Union Bank
    "hU8dCDBsTF0",  # Tata Capital Education Loan
    "aJ3SgfEZofc",  # 0% Interest Education Loan
    "MyjveOu8kio",  # Tax Benefits Section 80E
    "nSWPtq01Uww",  # Axis Bank Student Loan
    "EaKu2tLInX4",  # US Health Insurance
    "qYMTZl2xgUs",  # Loan Approved in 5 Days
    "9VwwQe-_kRc",  # IDFC First Bank Loan
    "qy4ZOnsy90A",  # Margin Money Explained
    "xKfTDUHaveQ",  # Top Scholarships
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
TONE_PROFILE_PATH = os.path.join(PROMPTS_DIR, "tone_profile.json")

def get_transcripts(video_ids: List[str]) -> List[str]:
    """Fetches transcripts for a list of YouTube video IDs."""
    transcripts = []
    api = YouTubeTranscriptApi()
    for video_id in video_ids:
        try:
            transcript_list = api.fetch(video_id, languages=['en', 'en-IN', 'hi'])
            text_blocks = [snippet.text for snippet in transcript_list]
            transcripts.append(" ".join(text_blocks))
            logger.info(f"Successfully fetched transcript for video {video_id}")
        except Exception as e:
            error_name = type(e).__name__
            if 'Disabled' in error_name or 'NotFound' in error_name:
                logger.warning(f"Transcripts unavailable for video {video_id}: {error_name}. Skipping.")
            elif 'IpBlocked' in error_name:
                logger.warning(f"YouTube IP blocked for video {video_id}. Skipping remaining videos.")
                break
            else:
                logger.error(f"Error fetching transcript for video {video_id}: {error_name}: {e}")
    return transcripts

def extract_tone_profile(transcripts: List[str]) -> Dict:
    """Uses Gemini to parse transcripts and build the tone profile JSON."""
    if not transcripts:
        logger.error("No transcripts available to analyze.")
        return {}

    # Read the prompt template
    prompt_path = os.path.join(PROMPTS_DIR, "tone_extraction_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Use 2000 words per transcript for richer voice data (Gemini handles large contexts)
    truncated_transcripts = []
    for t in transcripts:
        words = t.split()
        truncated = " ".join(words[:2000])
        truncated_transcripts.append(f"--- TRANSCRIPT START ---\\n{truncated}\\n--- TRANSCRIPT END ---")

    combined_transcripts = "\\n\\n".join(truncated_transcripts)
    final_prompt = prompt_template.replace("{transcripts}", combined_transcripts)

    # Make the API call to Gemini
    api_key = gemini_keys.current()
    if not api_key:
        logger.error("No Gemini API key available.")
        return {}

    genai.configure(api_key=api_key)
    # Using gemini-2.5-flash for analytical task
    model = genai.GenerativeModel("gemini-2.5-flash")

    try:
        response = model.generate_content(
            final_prompt,
            generation_config=os.getenv("VERCEL") and {"temperature": 0.2} or genai.types.GenerationConfig(
                temperature=0.2, # Low temp for analytical task
            )
        )
        
        raw_text = response.text.strip()
        # Clean up if Gemini wrapped it in markdown code blocks
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        profile = json.loads(raw_text.strip())
        
        # Save it
        with open(TONE_PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
            
        logger.info("Successfully extracted and saved tone profile.")
        return profile
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini tone response as JSON: {e}\\nRaw response: {response.text}")
        return {}
    except Exception as e:
        logger.error(f"Error calling Gemini for tone extraction: {e}")
        return {}

def load_tone_profile() -> Dict:
    """Loads existing tone profile, or generates a new one if missing."""
    if os.path.exists(TONE_PROFILE_PATH):
        try:
            with open(TONE_PROFILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load existing tone profile: {e}")
            
    # If missing or broken, try generating
    logger.info("Tone profile not found. Extracting from YouTube...")
    transcripts = get_transcripts(VIDEO_IDS)
    if transcripts:
        return extract_tone_profile(transcripts)
        
    logger.error("Could not fetch transcripts. Returning empty tone profile.")
    return {}
