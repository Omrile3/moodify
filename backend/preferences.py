"""Functions for handling user preferences and preference extraction."""

from typing import Dict, Optional, List, Tuple
from constants import PREFERENCE_FIELDS
from extraction import extract_preferences_raw, process_preferences

def extract_user_preferences(message: str, api_key: str, target_preference: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Extract preferences from a single message.
    
    Args:
        message: User input message
        api_key: OpenAI API key for preference extraction
        target_preference: Specific preference being asked about
    
    Returns:
        Dictionary with extracted preferences or None for unspecified preferences
    """
    # Extract raw preferences from the message with target context
    raw_preferences = extract_preferences_raw(message, api_key, target_preference)
    # Process them with the message context and target preference
    return process_preferences(raw_preferences, message, target_preference)

def update_session_preferences(session: dict, extracted: dict, target_preference: Optional[str] = None) -> None:
    """
    Update session with extracted preferences.
    
    Args:
        session: Current session dictionary
        extracted: Dictionary of extracted preferences
    """
    for field in PREFERENCE_FIELDS:
        # Always update if this is the target preference or if preference isn't set yet
        if (field == target_preference) or (not _is_preference_set(session, field)):
            if extracted.get(field):
                session[field] = extracted[field]
                session[f"no_pref_{field}"] = False
            # If GPT returned None for this field or marked it as "not music"
            elif extracted.get("_not_music") or any(extracted.get(k) and extracted[k] is None for k in PREFERENCE_FIELDS):
                if field == target_preference:
                    session[f"no_pref_{field}"] = True
                    session[field] = None

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
