"""Functions for handling user preferences and preference extraction."""

from typing import Dict, Optional, List, Tuple
from .constants import (
    PREFERENCE_FIELDS, 
    NO_PREF_WORDS,
    VAGUE_TO_MOOD,
    MOODS,
    GENRES
)
from .utils import extract_preferences_from_message, fuzzy_match_word

def extract_user_preferences(message: str, api_key: str) -> Dict[str, Optional[str]]:
    """
    Extract all preferences from a single message.
    
    Args:
        message: User input message
        api_key: OpenAI API key for preference extraction
    
    Returns:
        Dictionary with extracted preferences or None for unspecified preferences
    """
    extracted = extract_preferences_from_message(message, api_key)
    return {field: extracted.get(field) for field in PREFERENCE_FIELDS}

def update_session_preferences(session: dict, extracted: dict) -> None:
    """
    Update session with extracted preferences.
    
    Args:
        session: Current session dictionary
        extracted: Dictionary of extracted preferences
    """
    for field in PREFERENCE_FIELDS:
        if not _is_preference_set(session, field):
            if extracted.get(field):
                session[field] = extracted[field]
                session[f"no_pref_{field}"] = False
            elif _has_no_preference_keywords(message):
                session[f"no_pref_{field}"] = True

def _is_preference_set(session: dict, field: str) -> bool:
    """
    Check if a preference field is already set.
    
    Args:
        session: Current session dictionary
        field: Preference field to check
    
    Returns:
        True if preference is set or marked as no preference
    """
    return session.get(field) is not None or session.get(f"no_pref_{field}", False)

def _has_no_preference_keywords(message: str) -> bool:
    """
    Check if message contains 'no preference' indicators.
    
    Args:
        message: User input message
    
    Returns:
        True if message indicates no preference
    """
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in NO_PREF_WORDS)

def has_all_preferences(session: dict) -> bool:
    """
    Check if all required preferences are present.
    
    Args:
        session: Current session dictionary
    
    Returns:
        True if all preferences are set or marked as no preference
    """
    return all(
        _is_preference_set(session, field)
        for field in PREFERENCE_FIELDS
    )

def get_missing_preferences(session: dict) -> List[str]:
    """
    Get list of missing preferences.
    
    Args:
        session: Current session dictionary
    
    Returns:
        List of preference fields that are not set
    """
    return [
        field for field in PREFERENCE_FIELDS 
        if not _is_preference_set(session, field)
    ]

def validate_preference(field: str, value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a preference value for a specific field.
    
    Args:
        field: Preference field to validate
        value: Value to validate
    
    Returns:
        Tuple of (is_valid, corrected_value)
    """
    if not value:
        return False, None
        
    value = value.lower().strip()
    
    if field == "mood":
        corrected = fuzzy_match_word(value, MOODS)
        if corrected:
            return True, corrected
        # Check vague mood mappings
        if value in VAGUE_TO_MOOD:
            return True, VAGUE_TO_MOOD[value]
            
    elif field == "genre":
        corrected = fuzzy_match_word(value, GENRES)
        if corrected:
            return True, corrected
            
    elif field == "tempo":
        if value in ["slow", "medium", "fast"]:
            return True, value
            
    elif field == "artist_or_song":
        return True, value
        
    return False, None
