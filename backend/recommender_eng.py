import pandas as pd
import numpy as np
import random
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from utils import (
    convert_tempo_to_bpm,
    bpm_to_tempo_category,
    fuzzy_match_artist_song,
    generate_chat_response,
    extract_preferences_from_message,
    map_free_text_to_mood,
    split_mode_category,
    build_recommendation_key,
    precompute_recommendation_map,
)

# Load and prepare dataset
DATA_PATH = "data/songs.csv"
df = pd.read_csv(DATA_PATH)

# Save original tempo for reference
df["tempo_raw"] = pd.to_numeric(df["tempo"], errors="coerce")

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
    def apply_filters(preferences, filter_tempo=True, filter_genre=True, exclude_artist=None):
        local_df = df.copy()
        print(f"Filtering — Tempo: {filter_tempo}, Genre: {filter_genre}")

        if preferences.get("mood") and preferences["mood"] not in MOOD_VECTORS:
            preferences["mood"] = map_free_text_to_mood(preferences["mood"])

        if preferences.get("artist_or_song"):
            print("Filtering by artist/song:", preferences["artist_or_song"])
            local_df = fuzzy_match_artist_song(local_df, preferences["artist_or_song"])

        if filter_genre and preferences.get("genre"):
            print("Filtering by genre:", preferences["genre"])
            local_df = local_df[local_df['playlist_genre'].str.lower() == preferences["genre"].lower()]

        if filter_tempo and preferences.get("tempo"):
            print("Filtering by tempo:", preferences["tempo"])
            bpm_range = convert_tempo_to_bpm(preferences["tempo"])
            local_df = local_df[(local_df['tempo_raw'] >= bpm_range[0]) & (local_df['tempo_raw'] <= bpm_range[1])]

        if preferences.get("mood") in MOOD_VECTORS and not local_df.empty:
            print("Applying mood vector similarity:", preferences["mood"])
            mood_vec = np.array(MOOD_VECTORS[preferences["mood"]]).reshape(1, -1)
            similarities = cosine_similarity(mood_vec, local_df[features].values).flatten()
            local_df["similarity"] = similarities
            local_df = local_df.sort_values(by="similarity", ascending=False)

        if exclude_artist:
            local_df = local_df[local_df["track_artist"].str.lower() != exclude_artist.lower()]
            print(f"Excluding artist from recommendations: {exclude_artist}")

        return local_df

    # Detect similarity intent
    exclude_artist = None
    if preferences.get("artist_or_song"):
        lowered = preferences["artist_or_song"].lower()
        similarity_request_keywords = [
            "similar to", "like", "vibe like", "in the style of",
            "another artist like", "by a similar artist", "reminiscent of", "same vibe as", "any artist"
        ]
        if any(kw in lowered for kw in similarity_request_keywords):
            for artist in df['track_artist'].dropna().unique():
                if artist.lower() in lowered:
                    exclude_artist = artist
                    preferences["artist_or_song"] = artist
                    print(f"Similarity request detected — using: {artist}, but excluding it in results.")
                    break

    filtered = apply_filters(preferences, filter_tempo=True, filter_genre=True, exclude_artist=exclude_artist)
    print("Strict filter result:", filtered.shape)

    if filtered.empty:
        print("No results — retrying without tempo...")
        filtered = apply_filters(preferences, filter_tempo=False, filter_genre=True, exclude_artist=exclude_artist)

    if filtered.empty:
        print("Still no results — retrying without tempo or genre...")
        filtered = apply_filters(preferences, filter_tempo=False, filter_genre=False, exclude_artist=exclude_artist)

    history = preferences.get("history", [])
    top = None

    if filtered.empty:
        print("All filtering failed — fallback mode engaged.")
        genre = preferences.get("genre", "rock")
        tempo = preferences.get("tempo", "medium")
        mood = preferences.get("mood", "calm")
        energy = "energetic"
        key = build_recommendation_key(genre, mood, energy, tempo)
        fallback_list = recommendation_map.get(key, [])

        non_repeats = [song for song in fallback_list if (song["track_name"], song["track_artist"]) not in history]
        if non_repeats:
            top = random.choice(non_repeats)
            history.append((top["track_name"], top["track_artist"]))
        elif fallback_list:
            top = random.choice(fallback_list)
            history.append((top["track_name"], top["track_artist"]))
        else:
            return None
    else:
        for _, row in filtered.iterrows():
            if (row["track_name"], row["track_artist"]) not in history:
                top = row
                history.append((row["track_name"], row["track_artist"]))
                break
        if top is None:
            top = filtered.iloc[0]
            history.append((top["track_name"], top["track_artist"]))

    preferences["history"] = history

    tempo_category = bpm_to_tempo_category(top.get("tempo_raw", 100))
    response = {
        "song": top.get("track_name", "Unknown"),
        "artist": top.get("track_artist", "Unknown"),
        "genre": top.get("playlist_genre", "Unknown"),
        "mood": preferences.get("mood", "Unknown"),
        "tempo": tempo_category,
        "spotify_url": f"https://open.spotify.com/track/{top.get('track_id')}" if top.get("track_id") else None
    }

    if preferences.get("artist_or_song"):
        requested = preferences["artist_or_song"].lower()
        if top.get("track_artist", "").lower() != requested:
            response["artist_not_found"] = True
            response["requested_artist"] = requested

    return response
