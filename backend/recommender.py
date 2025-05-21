import pandas as pd
import os
from utils import convert_tempo_to_bpm, fuzzy_match_artist_song

# Load dataset once on module import
DATA_PATH = os.path.join("data", "songs.csv")
df = pd.read_csv(DATA_PATH)

# Ensure tempo column exists and BPMs are numeric
if 'tempo' in df.columns:
    df['tempo'] = pd.to_numeric(df['tempo'], errors='coerce')
else:
    raise ValueError("CSV must contain a 'tempo' column.")

def recommend_song(preferences: dict):
    filtered = df.copy()

    # Apply genre filter
    if preferences.get("genre"):
        filtered = filtered[filtered['genre'].str.lower() == preferences["genre"].lower()]

    # Apply mood filter
    if preferences.get("mood"):
        if "mood" in df.columns:
            filtered = filtered[filtered['mood'].str.lower() == preferences["mood"].lower()]

    # Apply tempo filter
    if preferences.get("tempo"):
        bpm_range = convert_tempo_to_bpm(preferences["tempo"])
        filtered = filtered[(filtered['tempo'] >= bpm_range[0]) & (filtered['tempo'] <= bpm_range[1])]

    # Artist/song fuzzy matching
    if preferences.get("artist_or_song"):
        filtered = fuzzy_match_artist_song(filtered, preferences["artist_or_song"])

    if filtered.empty:
        return None

    # Randomly select one result
    selected = filtered.sample(1).iloc[0]
    
    return {
        "song": selected.get("track_name", "Unknown"),
        "artist": selected.get("artist_name", "Unknown"),
        "genre": selected.get("genre", "Unknown"),
        "mood": selected.get("mood", "Unknown"),
        "tempo": selected.get("tempo", "Unknown")
    }
