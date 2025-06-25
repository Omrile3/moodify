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
    NO_PREF,
    NO_PREF_WORDS,
    VAGUE_TO_MOOD,
    OPENAI_MODEL,
    OPENAI_API_URL
)
from utils import fuzzy_match_word

empty_dict = {
    "genre": None,
    "mood": None,
    "tempo": None,
    "artist_or_song": None
}


def extract_preferences_raw(message: str, last_bot_response: Optional[str], api_key: str) -> dict:
    """
    Make raw GPT call to extract preferences from message.
    
    Args:
        message: User input message
        last_bot_response: Previous bot response for context
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
    genre_list_str = ", ".join(f'"{g}"' for g in sorted(GENRES))
    tempo_list_str = '"slow", "medium", "fast"'

    formatted_prompt = PREFERENCE_EXTRACTION_PROMPT.format(available_moods=mood_list_str, 
                                                           available_genres=genre_list_str,
                                                           available_tempos=tempo_list_str,
                                                           last_bot_response=last_bot_response or "No previous response",
                                                           user_message=message)

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
        log_dict_info("GPT extract preference response in text format", response=text)
        # Handle special responses
        if text in ["__NOT_ENGLISH__", "__NOT_MUSIC__"]:
            log_dict_info("Special response detected", response=text)
            return empty_dict

        # Extract JSON from response
        if text.startswith("```"):
            text = text.lstrip("`")
            text = text[text.find("{"):]
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            log_dict_error("No JSON object found in response", response=text)
            return empty_dict
        
        return json.loads(match.group(0))

    except Exception as e:
        log_dict_error("Error extracting preferences", error=str(e))
        return empty_dict

def process_preferences(
    extracted: dict
) -> Dict[str, Optional[str]]:
    """
    Process and validate extracted preferences.
    
    Args:
        extracted: Raw extracted preferences
        message: Original message for additional context
    
    Returns:
        Processed and validated preferences
    """
    if extracted == empty_dict:
        return empty_dict

    result = {}
    

    # # Check for "no preference" in original message using fuzzy matching
    # has_no_pref = False
    # if message:
    #     msg_lower = message.lower()
    #     has_no_pref = fuzzy_match_word(msg_lower, NO_PREF_WORDS) is not None

    # Process each preference field
    for field in ["genre", "mood", "tempo", "artist_or_song"]:
        val = extracted.get(field)

        if not val:
            result[field] = None
            continue

        val = val.lower().strip()

        if val in NO_PREF_WORDS:
            # If the value is a "no preference" word, set to None
            result[field] = NO_PREF
            continue

        # Handle field-specific validation
        if field == "mood":
            # Check vague mood mappings first
            if val in VAGUE_TO_MOOD.keys():
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
            
        elif field == "artist_or_song":
            result[field] = val
        else:
            log_dict_error("Unknown preference field", field=field, value=val)

    return result
