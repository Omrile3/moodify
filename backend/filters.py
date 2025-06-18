"""Functions for filtering song recommendations."""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from utils import convert_tempo_to_bpm, fuzzy_match_artist_song
from constants import SIMILARITY_KEYWORDS

def apply_mood_filter(df: pd.DataFrame, mood_vec: Optional[np.ndarray], features: List[str]) -> pd.DataFrame:
    """
    Apply mood-based filtering using cosine similarity.
    
    Args:
        df: DataFrame containing songs
        mood_vec: Mood vector to compare against
        features: List of audio features to use
        
    Returns:
        DataFrame sorted by mood similarity
    """
    if mood_vec is None or df.empty:
        return df
        
    similarities = cosine_similarity(
        np.array(mood_vec).reshape(1, -1), 
        df[features].values
    ).flatten()
    
    df = df.copy()
    df["similarity"] = similarities
    return df.sort_values(by="similarity", ascending=False)

def apply_genre_filter(df: pd.DataFrame, genre: Optional[str]) -> pd.DataFrame:
    """
    Filter songs by genre.
    
    Args:
        df: DataFrame containing songs
        genre: Preferred genre
        
    Returns:
        Filtered DataFrame
    """
    if not genre or df.empty:
        return df
    return df[df['playlist_genre'].str.lower() == genre.lower()]

def apply_tempo_filter(df: pd.DataFrame, tempo: Optional[str]) -> pd.DataFrame:
    """
    Filter songs by tempo range.
    
    Args:
        df: DataFrame containing songs
        tempo: Tempo preference (slow/medium/fast)
        
    Returns:
        Filtered DataFrame
    """
    if not tempo or df.empty:
        return df
        
    bpm_range = convert_tempo_to_bpm(tempo)
    return df[
        (df['tempo_raw'] >= bpm_range[0]) & 
        (df['tempo_raw'] <= bpm_range[1])
    ]

def apply_artist_filter(
    df: pd.DataFrame, 
    artist_or_song: Optional[str]
) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Filter songs by artist/song and detect similarity requests.
    
    Args:
        df: DataFrame containing songs
        artist_or_song: Artist or song preference
        
    Returns:
        Tuple of (filtered DataFrame, excluded artist)
    """
    if not artist_or_song:
        return df, None
        
    # Check for similarity request
    exclude_artist = None
    lowered = artist_or_song.lower()
    
    if any(kw in lowered for kw in SIMILARITY_KEYWORDS):
        for artist in df['track_artist'].dropna().unique():
            if artist.lower() in lowered:
                exclude_artist = artist
                break
                
    # Apply fuzzy matching
    filtered_df = fuzzy_match_artist_song(df, artist_or_song)
    
    # Exclude specified artist if similarity was requested
    if exclude_artist:
        filtered_df = filtered_df[
            filtered_df["track_artist"].str.lower() != exclude_artist.lower()
        ]
        
    return filtered_df, exclude_artist

def exclude_history(
    df: pd.DataFrame, 
    history: List[Tuple[str, str]]
) -> pd.DataFrame:
    """
    Exclude previously recommended songs.
    
    Args:
        df: DataFrame containing songs
        history: List of (song, artist) tuples to exclude
        
    Returns:
        Filtered DataFrame
    """
    if not history or df.empty:
        return df
        
    return df[
        ~df.apply(
            lambda row: (row["track_name"], row["track_artist"]) in history, 
            axis=1
        )
    ]

def apply_all_filters(
    df: pd.DataFrame,
    preferences: Dict[str, Any],
    features: List[str],
    mood_vector: Optional[np.ndarray] = None,
    strict: bool = True
) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Apply all filters to get song recommendations.
    
    Args:
        df: DataFrame containing songs
        preferences: Dictionary of user preferences
        features: List of audio features
        mood_vector: Optional mood vector for similarity
        strict: Whether to apply all filters strictly
        
    Returns:
        Tuple of (filtered DataFrame, excluded artist)
    """
    filtered = df.copy()
    exclude_artist = None
    
    # Apply artist filter first to check for similarity requests
    if preferences.get("artist_or_song"):
        filtered, exclude_artist = apply_artist_filter(
            filtered, 
            preferences["artist_or_song"]
        )
    
    # Apply other filters based on strictness
    if strict:
        if preferences.get("genre"):
            filtered = apply_genre_filter(filtered, preferences["genre"])
        if preferences.get("tempo"):
            filtered = apply_tempo_filter(filtered, preferences["tempo"])
    
    # Apply mood filtering if vector available
    if mood_vector is not None:
        filtered = apply_mood_filter(filtered, mood_vector, features)
    
    # Always exclude history
    filtered = exclude_history(filtered, preferences.get("history", []))
    
    return filtered, exclude_artist
