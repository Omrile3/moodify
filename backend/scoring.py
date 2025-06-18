"""Functions for calculating recommendation scores."""

from typing import Dict, Any, Optional
import pandas as pd
from constants import (
    SCORE_WEIGHTS,
    SAD_MOODS,
    HAPPY_MOODS,
    UPBEAT_WORDS,
    SLOW_WORDS
)

def normalize(val: Any) -> str:
    """Normalize input value to lowercase string."""
    if isinstance(val, str):
        return val.strip().lower()
    return str(val).strip().lower()

def calculate_genre_score(genre: str, pref_genre: Optional[str]) -> float:
    """Calculate genre match score."""
    if not pref_genre:
        return 0.0
        
    genre = normalize(genre)
    pref_genre = normalize(pref_genre)
    
    if pref_genre in genre:
        return SCORE_WEIGHTS["genre_match"]
    return 0.0

def calculate_mood_score(mood: str, pref_mood: Optional[str]) -> float:
    """Calculate mood match score."""
    if not pref_mood:
        return 0.0
        
    mood = normalize(mood)
    pref_mood = normalize(pref_mood)
    
    score = 0.0
    if pref_mood in mood:
        score += SCORE_WEIGHTS["mood_match"]
    elif pref_mood in SAD_MOODS:
        if any(x in mood for x in SAD_MOODS):
            score += SCORE_WEIGHTS["mood_match"]
        elif any(x in mood for x in HAPPY_MOODS):
            score += SCORE_WEIGHTS["mood_mismatch"]
    return score

def calculate_tempo_score(tempo: str, pref_tempo: Optional[str]) -> float:
    """Calculate tempo match score."""
    if not pref_tempo:
        return 0.0
        
    tempo = normalize(tempo)
    pref_tempo = normalize(pref_tempo)
    
    score = 0.0
    if pref_tempo in tempo:
        score += SCORE_WEIGHTS["tempo_match"]
    elif pref_tempo in SLOW_WORDS:
        if any(x in tempo for x in SLOW_WORDS):
            score += SCORE_WEIGHTS["tempo_match"]
        elif any(x in tempo for x in UPBEAT_WORDS):
            score += SCORE_WEIGHTS["tempo_mismatch"]
    return score

def calculate_artist_score(artist: str, track: str, pref: Optional[str]) -> float:
    """Calculate artist/track match score."""
    if not pref:
        return 0.0
        
    pref = normalize(pref)
    artist = normalize(artist)
    track = normalize(track)
    
    if pref in artist or pref in track:
        return SCORE_WEIGHTS["artist_match"]
    return 0.0

def calculate_popularity_score(popularity: Any) -> float:
    """Calculate popularity score component."""
    if popularity is None or pd.isna(popularity):
        return 0.0
    try:
        return float(popularity) / 100.0 * SCORE_WEIGHTS["popularity"]
    except (ValueError, TypeError):
        return 0.0

def calculate_weighted_score(song: Dict[str, Any], preferences: Dict[str, Any]) -> float:
    """
    Calculate overall weighted score for a song based on preferences.
    
    Args:
        song: Dictionary containing song information
        preferences: Dictionary containing user preferences
    
    Returns:
        Float score indicating how well the song matches preferences
    """
    score = 0.0
    
    # Get song attributes
    mood = song.get('mode_category', '') or song.get('mood', '')
    genre = song.get('playlist_genre', '')
    tempo = song.get('tempo_category', '')
    artist = song.get('track_artist', '')
    track = song.get('track_name', '')
    popularity = song.get('track_popularity', song.get('popularity'))
    
    # Calculate component scores
    score += calculate_genre_score(genre, preferences.get("genre"))
    score += calculate_mood_score(mood, preferences.get("mood"))
    score += calculate_tempo_score(tempo, preferences.get("tempo"))
    score += calculate_artist_score(artist, track, preferences.get("artist_or_song"))
    score += calculate_popularity_score(popularity)
    
    return score
