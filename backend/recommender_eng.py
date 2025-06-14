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

# --- Weighted recommendation logic ---
SAD_MOODS = {"sad", "melancholy", "down", "emotional", "blue", "heartbreak", "gloomy"}
HAPPY_MOODS = {"happy", "joy", "energetic", "upbeat", "party", "celebrate", "excited"}
UPBEAT_WORDS = {"upbeat", "party", "dance", "energetic", "celebrate", "hyped", "intense"}
SLOW_WORDS = {"slow", "ballad", "chill", "calm"}

def normalize(val):
    if isinstance(val, str):
        return val.strip().lower()
    return val

def weighted_score(row, prefs):
    # Mood, genre, tempo, artist
    mood = normalize(row.get('mode_category', '')) if 'mode_category' in row else ''
    genre = normalize(row.get('playlist_genre', '')) if 'playlist_genre' in row else ''
    tempo = normalize(row.get('tempo_category', '')) if 'tempo_category' in row else ''
    artist = normalize(row.get('track_artist', '')) if 'track_artist' in row else ''
    track_name = normalize(row.get('track_name', '')) if 'track_name' in row else ''
    # Extra: allow fallback to CSV field 'mood' if exists
    if not mood and 'mood' in row:
        mood = normalize(row.get('mood', ''))

    score = 0

    # GENRE + MOOD + TEMPO: Heavy weights
    if prefs.get("genre"):
        pgenre = normalize(prefs["genre"])
        if pgenre and pgenre in genre:
            score += 8

    if prefs.get("mood"):
        pmood = normalize(prefs["mood"])
        if pmood and pmood in mood:
            score += 8
        elif pmood in SAD_MOODS and any(x in mood for x in SAD_MOODS):
            score += 8
        elif pmood in SAD_MOODS and any(x in mood for x in HAPPY_MOODS):
            score -= 10  # Major penalty if sad mood requested but song is happy/upbeat
        elif pmood and pmood in mood:
            score += 3

    if prefs.get("tempo"):
        ptempo = normalize(prefs["tempo"])
        if ptempo and ptempo in tempo:
            score += 8
        elif ptempo in SLOW_WORDS and any(x in tempo for x in SLOW_WORDS):
            score += 8
        elif ptempo in SLOW_WORDS and any(x in tempo for x in UPBEAT_WORDS):
            score -= 5  # Penalty for slow preference but upbeat song
        elif ptempo and ptempo in tempo:
            score += 2

    # Artist: Bonus only if matches
    if prefs.get("artist_or_song"):
        query = normalize(prefs["artist_or_song"])
        if query and (query in artist or query in track_name):
            score += 2  # Bonus only

    # Popularity as tiebreaker
    pop_val = row.get('track_popularity', row.get('popularity', None))
    if pop_val is not None and not pd.isnull(pop_val):
        try:
            score += float(pop_val) / 100.0
        except Exception:
            pass

    # Extra exclusions for sad/slow
    if prefs.get("mood") and normalize(prefs["mood"]) in SAD_MOODS:
        if any(w in mood for w in HAPPY_MOODS | UPBEAT_WORDS):
            score -= 7

    if prefs.get("tempo") and normalize(prefs["tempo"]) in SLOW_WORDS:
        if any(w in tempo for w in UPBEAT_WORDS):
            score -= 3

    return score

def recommend_engine(preferences: dict):
    def apply_filters(preferences, filter_tempo=True, filter_genre=True, exclude_artist=None):
        local_df = df.copy()
        if preferences.get("mood") and preferences["mood"] not in MOOD_VECTORS:
            preferences["mood"] = map_free_text_to_mood(preferences["mood"])

        if preferences.get("artist_or_song"):
            local_df = fuzzy_match_artist_song(local_df, preferences["artist_or_song"])

        if filter_genre and preferences.get("genre"):
            local_df = local_df[local_df['playlist_genre'].str.lower() == preferences["genre"].lower()]

        if filter_tempo and preferences.get("tempo"):
            bpm_range = convert_tempo_to_bpm(preferences["tempo"])
            local_df = local_df[(local_df['tempo_raw'] >= bpm_range[0]) & (local_df['tempo_raw'] <= bpm_range[1])]

        if preferences.get("mood") in MOOD_VECTORS and not local_df.empty:
            mood_vec = np.array(MOOD_VECTORS[preferences["mood"]]).reshape(1, -1)
            similarities = cosine_similarity(mood_vec, local_df[features].values).flatten()
            local_df["similarity"] = similarities
            local_df = local_df.sort_values(by="similarity", ascending=False)

        if exclude_artist:
            local_df = local_df[local_df["track_artist"].str.lower() != exclude_artist.lower()]

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
                    break

    filtered = apply_filters(preferences, filter_tempo=True, filter_genre=True, exclude_artist=exclude_artist)
    if filtered.empty:
        filtered = apply_filters(preferences, filter_tempo=False, filter_genre=True, exclude_artist=exclude_artist)
    if filtered.empty:
        filtered = apply_filters(preferences, filter_tempo=False, filter_genre=False, exclude_artist=exclude_artist)

    history = preferences.get("history", [])
    top = None

    # --- Scoring logic ---
    if not filtered.empty:
        filtered = filtered.copy()
        filtered["weighted_score"] = filtered.apply(lambda row: weighted_score(row, preferences), axis=1)
        filtered = filtered.sort_values(by="weighted_score", ascending=False)
        # Pick first not in history
        for _, row in filtered.iterrows():
            if (row["track_name"], row["track_artist"]) not in history:
                top = row
                history.append((row["track_name"], row["track_artist"]))
                break
        if top is None and not filtered.empty:
            top = filtered.iloc[0]
            history.append((top["track_name"], top["track_artist"]))
    else:
        # fallback logic as before
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
