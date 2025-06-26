"""Functions for handling user preferences and preference extraction."""

from typing import Dict, Optional, List, Tuple
from constants import PREFERENCE_FIELDS, NO_PREF
from extraction import extract_preferences_raw, process_preferences
from log_utils import log_dict_info

def extract_user_preferences(session: dict, message: str, api_key: str) -> Dict[str, Optional[str]]:
    """
    Extract all preferences from a single message.
    
    Args:
        session: Current session dictionary containing context
        message: User input message
        api_key: OpenAI API key
    
    Returns:
        Dictionary with extracted preferences or None for unspecified preferences
    """
    # First extract raw preferences from the message with context
    last_bot_response = session.get("last_bot_response")
    gpt_extracted_preferences = extract_preferences_raw(message, last_bot_response, api_key)
    log_dict_info("gpt extracted preference converted to json format", preferences=gpt_extracted_preferences)
    # Then process them with the original message context for "no preference" detection
    validated_preferences = process_preferences(gpt_extracted_preferences)
    log_dict_info("validated preferences after processing", preferences=validated_preferences)
    return validated_preferences

def update_session_preferences(session: dict, extracted: dict) -> None:
    """
    Update session with extracted preferences.
    
    Args:
        session: Current session dictionary
        extracted: Dictionary of extracted preferences
    """
    for field in PREFERENCE_FIELDS:
    # Only update the field if it's present (not None) in extracted
        if field in extracted and extracted[field] is not None:
            value = extracted[field]
            if value == NO_PREF:
                session[field] = None
                session[f"no_pref_{field}"] = True
            else:
                session[field] = value
                session[f"no_pref_{field}"] = False
    # Do NOT overwrite previous value if not provided in the new extraction!


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


def all_extracted_are_none(extracted: Dict[str, Optional[str]]) -> bool:
    """
    Check if all extracted preferences are None.
    
    Args:
        extracted: Dictionary of extracted preferences
    
    Returns:
        True if all values in the dictionary are None
    """
    return all(value is None for value in extracted.values())
