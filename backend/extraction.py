"""Handles the extraction of preferences from user messages."""

import json
import re
import requests
from typing import Dict, Optional
from log_utils import log_dict_error, log_dict_info

from prompts import (
    PREFERENCE_EXTRACTION_PROMPT,
    SYSTEM_ROLES,
    GPT_SETTINGS
)
from constants import (
    MOODS,
    GENRES,
    NO_PREF_WORDS,
    VAGUE_TO_MOOD,
    OPENAI_MODEL,
    OPENAI_API_URL
)
from utils import fuzzy_match_word

def extract_preferences_raw(message: str, api_key: str) -> dict:
    """
    Make raw GPT call to extract preferences from message.
    
    Args:
        message: User input message
        api_key: OpenAI API key
    
    Returns:
        Raw dictionary of extracted preferences
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Format prompt with available moods
    mood_list_str = ", ".join(f'"{m}"' for m in sorted(MOODS))
    genere_list_str = ", ".join(f'"{g}"' for g in sorted(GENRES))
    tempo_list_str = '"slow", "medium", "fast"'

    formatted_prompt = PREFERENCE_EXTRACTION_PROMPT.format(available_moods=mood_list_str, 
                                                           available_genres=genere_list_str,
                                                           available_tempo=tempo_list_str,
                                                           user_message= message)

    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_ROLES['preference_extraction']},
            {"role": "user", "content": formatted_prompt}
        ],
        "temperature": GPT_SETTINGS['preference_extraction']['temperature'],
        "max_tokens": GPT_SETTINGS['preference_extraction']['max_tokens']
    }

    try:
        response = requests.post(
            OPENAI_API_URL,
            headers=headers,
            json=body
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"].strip()
        log_dict_info(f"GPT extract prefernce response: {text}")
        # Handle special responses
        if text in ["__NOT_ENGLISH__", "__NOT_MUSIC__"]:
            log_dict_info(f"Special response detected: {text}")
            return {
                "genre": None,
                "mood": None,
                "tempo": None,
                "artist_or_song": None,
                f"_{text.lower().strip('_')}": True
            }

        # Extract JSON from response
        if text.startswith("```"):
            text = text.lstrip("`")
            text = text[text.find("{"):]
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            log_dict_error("No JSON object found in response")
            raise ValueError("No JSON object found in response")
        
        return json.loads(match.group(0))

    except Exception as e:
        log_dict_error(f"Error extracting preferences: {e}")
        return {
            "genre": None,
            "mood": None,
            "tempo": None,
            "artist_or_song": None,
            "_error": str(e)
        }

def process_preferences(
    extracted: dict,
    message: Optional[str] = None
) -> Dict[str, Optional[str]]:
    """
    Process and validate extracted preferences.
    
    Args:
        extracted: Raw extracted preferences
        message: Original message for additional context
    
    Returns:
        Processed and validated preferences
    """
    result = {}
    
    # Handle special cases
    if any(extracted.get(k) for k in ["_not_english", "_not_music", "_error"]):
        log_dict_info("Special case detected in extracted preferences")
        return {
            "genre": None,
            "mood": None,
            "tempo": None,
            "artist_or_song": None,
            **{k: v for k, v in extracted.items() if k.startswith("_")}
        }

    # Check for "no preference" in original message using fuzzy matching
    has_no_pref = False
    if message:
        msg_lower = message.lower()
        has_no_pref = fuzzy_match_word(msg_lower, NO_PREF_WORDS) is not None

    # Process each preference field
    for field in ["genre", "mood", "tempo", "artist_or_song"]:
        val = extracted.get(field)
        
        if not val or has_no_pref:
            result[field] = None
            continue

        val = val.lower().strip()
        
        # Handle field-specific validation
        if field == "mood":
            # Check vague mood mappings first
            if val in VAGUE_TO_MOOD:
                val = VAGUE_TO_MOOD[val]
            # Then check against valid moods
            if val in MOODS:
                result[field] = val
            else:
                result[field] = None
                
        elif field == "genre":
            result[field] = val if val in GENRES else None
            
        elif field == "tempo":
            result[field] = val if val in ["slow", "medium", "fast"] else None
            
        else:  # artist_or_song
            result[field] = val

    return result
