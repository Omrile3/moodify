import pandas as pd
import numpy as np
import random
from sklearn.preprocessing import MinMaxScaler

from utils import (
    bpm_to_tempo_category,
    build_recommendation_key,
    precompute_recommendation_map,
    get_mood_vector
)
from constants import (
    DATA_PATH,
    AUDIO_FEATURES
)
from scoring import calculate_weighted_score
from filters import apply_all_filters
from constants import PREFERENCE_FIELDS
from log_utils import log_dict_info, log_dict_warning

def load_and_process_data() -> tuple[pd.DataFrame, dict]:
    """
    Load and preprocess the song dataset.
    
    Returns:
        Tuple of (processed DataFrame, recommendation map)
    """
    log_dict_info("Loading song dataset", path=DATA_PATH)
    df = pd.read_csv(DATA_PATH)

    # Convert tempo to numeric and handle missing values
    log_dict_info("Processing tempo data", total_rows=len(df))
    df["tempo_raw"] = pd.to_numeric(df["tempo"], errors="coerce")

    # Preprocess audio features
    log_dict_info("Processing audio features", 
                 features=AUDIO_FEATURES,
                 initial_rows=len(df))
    df = df.dropna(subset=AUDIO_FEATURES)
    df[AUDIO_FEATURES] = df[AUDIO_FEATURES].apply(pd.to_numeric, errors='coerce')
    df = df.dropna(subset=AUDIO_FEATURES)

    # Scale audio features
    log_dict_info("Scaling audio features", 
                 features=AUDIO_FEATURES,
                 scaler="MinMaxScaler")
    scaler = MinMaxScaler()
    df[AUDIO_FEATURES] = scaler.fit_transform(df[AUDIO_FEATURES])

    # Precompute recommendation map
    log_dict_info("Building recommendation map", 
                 total_songs=len(df),
                 unique_genres=len(df['playlist_genre'].unique()))
    recommendation_map = precompute_recommendation_map(df)
    
    log_dict_info("Data preprocessing complete",
                 final_rows=len(df),
                 feature_stats={
                     feature: {
                         "mean": float(df[feature].mean()),
                         "std": float(df[feature].std())
                     } for feature in AUDIO_FEATURES
                 })
    return df, recommendation_map

# Load processed data
df, recommendation_map = load_and_process_data()


def recommend_engine(preferences: dict, api_key: str):
    """
    Get song recommendations based on user preferences.
    
    Args:
        preferences: Dictionary of user preferences
        api_key: OpenAI API key for mood vector generation
    
    Returns:
        Dictionary containing recommended song information
    """
    # Validate preferences
    for field in PREFERENCE_FIELDS:
        if not preferences.get(field) and not preferences.get(f"no_pref_{field}", False):
            log_dict_warning("Missing required preference", 
                           field=field,
                           preferences=preferences)
            return None
            
    # Get mood vector if mood preference exists
    mood_vec = None
    if preferences.get("mood"):
        log_dict_info("Getting mood vector", 
                     mood=preferences['mood'],
                     session_id=preferences.get('session_id'))
        mood_vec = get_mood_vector(preferences["mood"], api_key)
        
    # Apply filters with increasing flexibility
    history = preferences.get("history", [])
    filtered, exclude_artist = apply_all_filters(
        df, preferences, AUDIO_FEATURES, mood_vec, strict=True
    )
    
    if filtered.empty:
        log_dict_info("No strict matches, relaxing filters",
                     preferences=preferences,
                     history_length=len(history),
                     mood_vector_present=mood_vec is not None)
        filtered, exclude_artist = apply_all_filters(
            df, preferences, AUDIO_FEATURES, mood_vec, strict=False
        )
        
    top = None
    if not filtered.empty:
        # Calculate scores for filtered songs
        filtered = filtered.copy()
        filtered["weighted_score"] = filtered.apply(
            lambda row: calculate_weighted_score(row, preferences),
            axis=1
        )
        filtered = filtered.sort_values(by="weighted_score", ascending=False)
        
        # Try to find first non-repeated song
        for _, row in filtered.iterrows():
            if (row["track_name"], row["track_artist"]) not in history:
                top = row
                history.append((row["track_name"], row["track_artist"]))
                log_dict_info("Found non-repeated song", 
                            song=row['track_name'],
                            artist=row['track_artist'],
                            score=row['weighted_score'])
                break
                
        # If all are repeats, take the top one
        if top is None and not filtered.empty:
            top = filtered.iloc[0]
            history.append((top["track_name"], top["track_artist"]))
            log_dict_info("Using repeated song",
                       song=top['track_name'],
                       artist=top['track_artist'],
                       weighted_score=float(top['weighted_score']),
                       reason="all_songs_repeated")
    
    # Use fallback recommendation if no matches found
    if top is None:
        genre = preferences.get("genre", None)
        tempo = preferences.get("tempo", None)

        if genre and genre.lower() != "no preference":
            filtered_genre = df[df["playlist_genre"].str.lower() == genre.lower()]
        else:
            filtered_genre = df

        if tempo and tempo.lower() != "no preference":
            filtered_tempo = filtered_genre[filtered_genre["tempo_raw"].apply(
                lambda t: bpm_to_tempo_category(t).lower() == tempo.lower()
            )]
        else:
            filtered_tempo = filtered_genre

        fallback_list = filtered_tempo.sample(frac=1).to_dict("records")
        
        if fallback_list:
            top = random.choice(fallback_list)
            history.append((top["track_name"], top["track_artist"]))
            log_dict_info("Using fallback song",
                       song=top["track_name"],
                       artist=top["track_artist"],
                       genre=top["playlist_genre"],
                       tempo=bpm_to_tempo_category(top["tempo_raw"]),
                       history_length=len(history))
        else:
            log_dict_warning("No recommendations found",
                          preferences=preferences,
                          history_length=len(history))
            return None

    # Update history and prepare response
    preferences["history"] = history
    
    # Get tempo category and Spotify URL
    tempo_category = bpm_to_tempo_category(top.get("tempo_raw", 100))
    track_id = top.get("track_id", "").strip()
    spotify_url = None
    
    if (track_id and 
        isinstance(track_id, str) and 
        track_id.lower() != "none" and 
        len(track_id) == 22 and 
        track_id.isalnum()
    ):
        spotify_url = f"https://open.spotify.com/track/{track_id}"
        log_dict_info("Generated Spotify URL",
                    track_id=track_id,
                    spotify_url=spotify_url,
                    song=top.get("track_name"))

    # Build response
    response = {
        "song": top.get("track_name", "Unknown"),
        "artist": top.get("track_artist", "Unknown"),
        "genre": top.get("playlist_genre", "Unknown"),
        "mood": preferences.get("mood", "Unknown"),
        "tempo": tempo_category,
        "spotify_url": spotify_url
    }

    # Add artist not found flag if needed
    if preferences.get("artist_or_song"):
        requested = preferences["artist_or_song"].lower()
        if top.get("track_artist", "").lower() != requested:
            response["artist_not_found"] = True
            response["requested_artist"] = requested
            log_dict_info("Artist not found, suggesting alternative",
                       requested_artist=requested,
                       suggested_artist=top.get("track_artist"),
                       song=top.get("track_name"))

    log_dict_info("Final recommendation",
                song=response['song'],
                artist=response['artist'],
                genre=response['genre'],
                mood=response['mood'],
                tempo=response['tempo'],
                has_spotify_url=bool(spotify_url))
    return response
