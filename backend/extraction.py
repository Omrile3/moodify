"""Handles the extraction of preferences from user messages."""

import json
import re
import requests
from typing import Dict, Optional

from prompts import (
    PREFERENCE_EXTRACTION_PROMPT,
    FOCUSED_PREFERENCE_EXTRACTION_PROMPT,
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

def extract_preferences_raw(message: str, api_key: str, target_preference: Optional[str] = None) -> dict:
    """
    Make raw GPT call to extract preferences from message.
    
    Args:
        message: User input message
        api_key: OpenAI API key
        target_preference: Specific preference being asked about (genre/mood/tempo/artist_or_song)
    
    Returns:
        Raw dictionary of extracted preferences
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Format prompt with available moods
    mood_list_str = ", ".join(f'"{m}"' for m in sorted(MOODS))
    
    # Use focused prompt if targeting specific preference
    if target_preference:
        formatted_prompt = FOCUSED_PREFERENCE_EXTRACTION_PROMPT.format(
            available_moods=mood_list_str,
            target_preference=target_preference
        )
    else:
        formatted_prompt = PREFERENCE_EXTRACTION_PROMPT.format(available_moods=mood_list_str)

    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_ROLES['preference_extraction']},
            {"role": "user", "content": formatted_prompt + f'\nInput: "{message}"'}
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

        # Handle special responses
        if text in ["__NOT_ENGLISH__", "__NOT_MUSIC__"]:
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
            raise ValueError("No JSON object found in response")
        
        return json.loads(match.group(0))

    except Exception as e:
        print(f"Preference extraction failed: {e}")
        return {
            "genre": None,
            "mood": None,
            "tempo": None,
            "artist_or_song": None,
            "_error": str(e)
        }

def extract_user_preferences(
    message: str, 
    api_key: str,
    target_preference: Optional[str] = None
) -> Dict[str, Optional[str]]:
    """
    Extract preferences from a single message.
    
    Args:
        message: User input message
        api_key: OpenAI API key
        target_preference: Specific preference being asked about
    
    Returns:
        Dictionary of processed and validated preferences
    """
    # First extract raw preferences from the message
    raw_preferences = extract_preferences_raw(message, api_key, target_preference)
    # Then process them with the original message context and target preference
    return process_preferences(raw_preferences, message, target_preference)


def process_preferences(
    extracted: dict,
    message: Optional[str] = None,
    target_preference: Optional[str] = None
) -> Dict[str, Optional[str]]:
    """
    Process and validate extracted preferences.
    
    Args:
        extracted: Raw extracted preferences
        message: Original message for additional context
        target_preference: Specific preference being asked about
    
    Returns:
        Processed and validated preferences
    """
    result = {}
    
    # Handle special cases
    if any(extracted.get(k) for k in ["_not_english", "_not_music", "_error"]):
        return {
            "genre": None,
            "mood": None,
            "tempo": None,
            "artist_or_song": None,
            **{k: v for k, v in extracted.items() if k.startswith("_")}
        }

    # Check for "no preference" in original message
    has_no_pref = False
    if message:
        msg_lower = message.lower()
        has_no_pref = any(word in msg_lower for word in NO_PREF_WORDS)

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
