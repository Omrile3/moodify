import pandas as pd
import numpy as np
import random
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from utils import (
    convert_tempo_to_bpm,
    fuzzy_match_artist_song,
    generate_chat_response,
    extract_preferences_from_message,
    map_free_text_to_mood,
    split_mode_category,
    build_recommendation_key,
    precompute_recommendation_map,
    search_spotify_preview
)

# Load and prepare dataset
DATA_PATH = "data/songs.csv"
df = pd.read_csv(DATA_PATH)

# Normalize feature columns
features = ['valence', 'energy', 'danceability', 'acousticness', 'tempo']
df = df.dropna(subset=features)
df[features] = df[features].apply(pd.to_numeric, errors='coerce')
df = df.dropna(subset=features)
scaler = MinMaxScaler()
df[features] = scaler.fit_transform(df[features])

# Mood vectors for cosine similarity
MOOD_VECTORS = {
    "happy": [0.9, 0.8, 0.7, 0.2, 0.6],
    "sad": [0.2, 0.3, 0.2, 0.6, 0.4],
    "energetic": [0.7, 0.9, 0.8, 0.1, 0.8],
    "calm": [0.5, 0.4, 0.3, 0.7, 0.5]
}

# Fallback recommendation map
recommendation_map = precompute_recommendation_map(df)

def recommend_engine(preferences: dict, session_memory=None):
    if session_memory is None:
        session_memory = set()
    filtered = df.copy()

    if preferences.get("mood") and preferences["mood"] not in MOOD_VECTORS:
        preferences["mood"] = map_free_text_to_mood(preferences["mood"])

    if preferences.get("artist_or_song"):
        filtered = fuzzy_match_artist_song(filtered, preferences["artist_or_song"])

    if preferences.get("genre"):
        genre_filter = preferences["genre"].lower()
        genre_matched = filtered[filtered['playlist_genre'].str.lower() == genre_filter]
        if not genre_matched.empty:
            filtered = genre_matched

    if preferences.get("tempo"):
        bpm_range = convert_tempo_to_bpm(preferences["tempo"])
        filtered = filtered[(filtered['tempo'] >= bpm_range[0]) & (filtered['tempo'] <= bpm_range[1])]

    if preferences.get("mood") in MOOD_VECTORS and not filtered.empty:
        mood_vec = np.array(MOOD_VECTORS[preferences["mood"]]).reshape(1, -1)
        similarities = cosine_similarity(mood_vec, filtered[features].values).flatten()
        filtered["similarity"] = similarities
        filtered = filtered.sort_values(by="similarity", ascending=False)
    elif 'track_popularity' in filtered.columns:
        filtered = filtered.sort_values(by='track_popularity', ascending=False)

    if not filtered.empty:
        filtered = filtered[~filtered['track_name'].isin(session_memory)]
        if filtered.empty:
            session_memory.clear()
            filtered = df.copy()

        top = filtered.iloc[0]
    else:
        genre = preferences.get("genre", "rock")
        tempo = preferences.get("tempo", "medium")
        mood = preferences.get("mood", "calm")
        energy = "energetic"
        key = build_recommendation_key(genre, mood, energy, tempo)
        fallback_list = recommendation_map.get(key, [])
        if not fallback_list:
            return None
        top = random.choice(fallback_list)

    # Enrich with Spotify preview
    preview_data = search_spotify_preview(top.get("track_name", ""), top.get("track_artist", ""))

    return {
        "song": top.get("track_name", "Unknown"),
        "artist": top.get("track_artist", "Unknown"),
        "genre": top.get("playlist_genre", "Unknown"),
        "mood": preferences.get("mood", "Unknown"),
        "tempo": top.get("tempo", "Unknown"),
        "spotify_url": preview_data.get("spotify_url"),
        "preview_url": preview_data.get("preview_url")
    }
