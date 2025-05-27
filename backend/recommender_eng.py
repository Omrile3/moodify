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
    precompute_recommendation_map
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

# Mood vectors
MOOD_VECTORS = {
    "happy": [0.9, 0.8, 0.7, 0.2, 0.6],
    "sad": [0.2, 0.3, 0.2, 0.6, 0.4],
    "energetic": [0.7, 0.9, 0.8, 0.1, 0.8],
    "calm": [0.5, 0.4, 0.3, 0.7, 0.5]
}

recommendation_map = precompute_recommendation_map(df)

def recommend_engine(preferences: dict):
    filtered = df.copy()

    print("Initial DataFrame size:", filtered.shape)

    if preferences.get("mood") and preferences["mood"] not in MOOD_VECTORS:
        preferences["mood"] = map_free_text_to_mood(preferences["mood"])

    print("After mood mapping:", filtered.shape)

    if preferences.get("artist_or_song"):
        print("Filtering by artist or song:", preferences["artist_or_song"])
        filtered = fuzzy_match_artist_song(filtered, preferences["artist_or_song"])

    print("After artist/song filtering:", filtered.shape)

    if preferences.get("genre"):
        print("Filtering by genre:", preferences["genre"])
        filtered = filtered[filtered['playlist_genre'].str.lower() == preferences["genre"].lower()]

    print("After genre filtering:", filtered.shape)

    if preferences.get("tempo"):
        print("Filtering by tempo:", preferences["tempo"])
        bpm_range = convert_tempo_to_bpm(preferences["tempo"])
        filtered = filtered[(filtered['tempo'] >= bpm_range[0]) & (filtered['tempo'] <= bpm_range[1])]

    print("After tempo filtering:", filtered.shape)

    if preferences.get("mood") in MOOD_VECTORS:
        print("Applying mood vector similarity for mood:", preferences["mood"])
        if not filtered.empty:
            mood_vec = np.array(MOOD_VECTORS[preferences["mood"]]).reshape(1, -1)
            similarities = cosine_similarity(mood_vec, filtered[features].values).flatten()
            filtered["similarity"] = similarities
            filtered = filtered.sort_values(by="similarity", ascending=False)
        else:
            print("Filtered DataFrame is empty. Skipping mood vector similarity.")

    if not filtered.empty:
        last_song = preferences.get("last_song")
        last_artist = preferences.get("last_artist")
        for _, row in filtered.iterrows():
            if row["track_name"] != last_song or row["track_artist"] != last_artist:
                top = row
                break
        else:
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

    return {
        "song": top.get("track_name", "Unknown"),
        "artist": top.get("track_artist", "Unknown"),
        "genre": top.get("playlist_genre", "Unknown"),
        "mood": preferences.get("mood", "Unknown"),
        "tempo": top.get("tempo", "Unknown")
    }
