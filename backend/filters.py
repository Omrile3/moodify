"""Functions for filtering song recommendations."""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from utils import convert_tempo_to_bpm, fuzzy_match_artist_song
from constants import SIMILARITY_KEYWORDS
from log_utils import log_dict_info, log_dict_warning

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
        log_dict_info("Skipping mood filter", reason="no_mood_vector" if mood_vec is None else "empty_dataframe")
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
        log_dict_info("Skipping genre filter", reason="no_genre" if not genre else "empty_dataframe")
        return df
        
    filtered = df[df['playlist_genre'].str.lower() == genre.lower()]
    log_dict_info("Applied genre filter", 
                genre=genre,
                initial_count=len(df),
                filtered_count=len(filtered))
    return filtered

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
        log_dict_info("Skipping tempo filter", reason="no_tempo" if not tempo else "empty_dataframe")
        return df
        
    bpm_range = convert_tempo_to_bpm(tempo)
    filtered = df[
        (df['tempo_raw'] >= bpm_range[0]) & 
        (df['tempo_raw'] <= bpm_range[1])
    ]
    
    log_dict_info("Applied tempo filter",
                tempo=tempo,
                bpm_range=bpm_range,
                initial_count=len(df),
                filtered_count=len(filtered))
    return filtered

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
    log_dict_info("Starting artist/song filter", 
                artist_or_song=artist_or_song,
                initial_count=len(df))
    if not artist_or_song:
        log_dict_info("Skipping artist/song filter", reason="no_artist_or_song")
        return df, None
        
    # Check for similarity request
    exclude_artist = None
    lowered = artist_or_song.lower()
    
    if any(kw in lowered for kw in SIMILARITY_KEYWORDS):
        log_dict_info("Detected similarity request", request=lowered)
        for artist in df['track_artist'].dropna().unique():
            if artist.lower() in lowered:
                exclude_artist = artist
                log_dict_info("Found artist to exclude", artist=exclude_artist)
                break
                
    # Apply fuzzy matching
    filtered_df = fuzzy_match_artist_song(df, artist_or_song)
    
    # Exclude specified artist if similarity was requested
    if exclude_artist:
        filtered_df = filtered_df[
            filtered_df["track_artist"].str.lower() != exclude_artist.lower()
        ]
        
    log_dict_info("Applied artist/song filter",
                filtered_count=len(filtered_df),
                excluded_artist=exclude_artist,
                similarity_requested=bool(exclude_artist))
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
        log_dict_info("Skipping history exclusion", 
                    reason="no_history" if not history else "empty_dataframe")
        return df
    
    filtered = df[
        ~df.apply(
            lambda row: (row["track_name"], row["track_artist"]) in history, 
            axis=1
        )
    ]
    
    log_dict_info("Applied history exclusion",
                initial_count=len(df),
                filtered_count=len(filtered),
                history_size=len(history))
    return filtered

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
    log_dict_info("Starting filter pipeline",
                initial_songs=len(df),
                preferences={k: v for k, v in preferences.items() if k != "history"},
                strict_mode=strict,
                has_mood_vector=mood_vector is not None)
                
    filtered = df.copy()
    exclude_artist = None
    
    # Apply artist filter first to check for similarity requests
    if preferences.get("artist_or_song"):
        filtered, exclude_artist = apply_artist_filter(
            filtered, 
            preferences["artist_or_song"]
        )
        if filtered.empty:
            log_dict_info("No matches found with artist filter, omitting artist preference")
            preferences["artist_or_song"] = None
    
    # Apply other filters based on strictness
    if strict:
        if preferences.get("genre"):
            filtered = apply_genre_filter(filtered, preferences["genre"])
            if filtered.empty:
                log_dict_info("No matches found with genre filter, omitting genre preference")
                preferences["genre"] = None
        if preferences.get("tempo"):
            filtered = apply_tempo_filter(filtered, preferences["tempo"])
            if filtered.empty:
                log_dict_info("No matches found with tempo filter, omitting tempo preference")
                preferences["tempo"] = None
    
    # Apply mood filtering if vector available
    if mood_vector is not None:
        filtered = apply_mood_filter(filtered, mood_vector, features)
    
    # Always exclude history
    filtered = exclude_history(filtered, preferences.get("history", []))
    
    # Fallback: If no preferences are set, return random song
    if all(value is None for value in preferences.values()):
        log_dict_info("No preferences set, returning random song")
        return filtered.sample(n=1), None
    
    log_dict_info("Filter pipeline complete",
                initial_count=len(df),
                final_count=len(filtered),
                excluded_artist=exclude_artist,
                filters_applied={
                    "artist": bool(preferences.get("artist_or_song")),
                    "genre": bool(preferences.get("genre")) and strict,
                    "tempo": bool(preferences.get("tempo")) and strict,
                    "mood": mood_vector is not None,
                    "history": bool(preferences.get("history"))
                })
    return filtered, exclude_artist
