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

# Precompute recommendation map for fallback
recommendation_map = precompute_recommendation_map(df)

def recommend_engine(preferences: dict, session_memory=None):
    if session_memory is None:
        session_memory = set()

    filtered = df.copy()
    query = preferences.get("artist_or_song")

    # Normalize mood if needed
    if preferences.get("mood") and preferences["mood"] not in MOOD_VECTORS:
        preferences["mood"] = map_free_text_to_mood(preferences["mood"])

    # Check if not enough info
    missing_keys = [k for k in ["artist_or_song", "genre", "mood", "tempo"] if not preferences.get(k)]
    if len(missing_keys) >= 3:
        preferences["note"] = (
            "🎯 I need a bit more to recommend something great. "
            "Could you tell me one or more of the following: your mood, favorite artist, genre, or tempo?"
        )
        return {
            "song": "N/A",
            "artist": "N/A",
            "genre": "N/A",
            "mood": preferences.get("mood", "Unknown"),
            "tempo": "N/A",
            "spotify_url": None,
            "preview_url": None,
            "note": preferences["note"]
        }

    print(f"Initial DataFrame size: {filtered.shape}")
    # Filter by artist or song
    if query:
        query = query.lower().strip()
        artist_matches = df[df["track_artist"].str.lower().str.contains(query, na=False)]
        song_matches = df[df["track_name"].str.lower().str.contains(query, na=False)]

        if not artist_matches.empty:
            filtered = artist_matches
            preferences["note"] = f"🎶 Here's a song by {query.title()} you might enjoy."
        elif not song_matches.empty:
            filtered = song_matches
        else:
            fuzzy_matches = fuzzy_match_artist_song(df, query)
            if not fuzzy_matches.empty:
                filtered = fuzzy_matches
                preferences["note"] = f"🔍 Couldn't find an exact match for '{query}', but here are similar tracks."
            else:
                preferences["note"] = f"⚠️ Couldn't find anything related to '{query}'. Showing popular songs."
                filtered = df.copy()

    print(f"After artist/song filtering: {filtered.shape}")
    # Filter by genre
    if preferences.get("genre"):
        genre = preferences["genre"].lower()
        filtered = filtered[filtered['playlist_genre'].str.lower() == genre] or filtered

    print(f"After genre filtering: {filtered.shape}")
    # Filter by tempo
    if preferences.get("tempo"):
        min_bpm, max_bpm = convert_tempo_to_bpm(preferences["tempo"])
        filtered = filtered[(filtered["tempo"] >= min_bpm) & (filtered["tempo"] <= max_bpm)]

    print(f"After tempo filtering: {filtered.shape}")
    # Mood cosine similarity sort
    if preferences.get("mood") in MOOD_VECTORS and not filtered.empty:
        mood_vec = np.array(MOOD_VECTORS[preferences["mood"]]).reshape(1, -1)
        similarities = cosine_similarity(mood_vec, filtered[features].values).flatten()
        filtered["similarity"] = similarities
        filtered = filtered.sort_values(by="similarity", ascending=False)
    elif "track_popularity" in filtered.columns:
        filtered = filtered.sort_values(by="track_popularity", ascending=False)

    # Remove already recommended
    filtered = filtered[~filtered["track_name"].isin(session_memory)]

    print(f"After mood similarity filtering: {filtered.shape}")
    if not filtered.empty:
        top = filtered.iloc[0]
        session_memory.add(top["track_name"])
    else:
        # Fallback if nothing left
        genre = preferences.get("genre", "rock")
        tempo = preferences.get("tempo", "medium")
        mood = preferences.get("mood", "calm")
        energy = "energetic"
        key = build_recommendation_key(genre, mood, energy, tempo)
        fallback_list = recommendation_map.get(key, [])
        if not fallback_list:
            return None
        top = random.choice(fallback_list)

    # Spotify preview info
    preview = search_spotify_preview(top.get("track_name", ""), top.get("track_artist", ""))

    return {
        "song": top.get("track_name", "Unknown Song"),
        "artist": top.get("track_artist", "Unknown Artist"),
        "genre": top.get("playlist_genre", "Unknown"),
        "mood": preferences.get("mood", "Unknown"),
        "tempo": top.get("tempo", "Unknown"),
        "spotify_url": preview.get("spotify_url"),
        "preview_url": preview.get("preview_url"),
        "note": preferences.get("note", None)
    }
