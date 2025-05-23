import os
import base64
import requests
import json
import re
import pandas as pd
import numpy as np
from functools import lru_cache
from sklearn.metrics.pairwise import cosine_similarity

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

@lru_cache(maxsize=1)
def get_spotify_access_token():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    token_url = "https://accounts.spotify.com/api/token"

    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_header}"}
    data = {"grant_type": "client_credentials"}

    try:
        response = requests.post(token_url, headers=headers, data=data)
        return response.json().get("access_token")
    except Exception as e:
        print("Spotify token error:", e)
        return None

def search_spotify_preview(song_name, artist_name):
    token = get_spotify_access_token()
    if not token:
        return {}

    query = f"{song_name} {artist_name}"
    url = f"https://api.spotify.com/v1/search?q={requests.utils.quote(query)}&type=track&limit=1"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        res = requests.get(url, headers=headers)
        items = res.json().get("tracks", {}).get("items", [])
        if not items:
            return {}
        track = items[0]
        return {
            "spotify_url": track["external_urls"].get("spotify"),
            "preview_url": track.get("preview_url"),
            "album": track.get("album", {}).get("name"),
            "cover_art": track.get("album", {}).get("images", [{}])[0].get("url")
        }
    except Exception as e:
        print("Spotify search error:", e)
        return {}

def convert_tempo_to_bpm(tempo_category: str) -> tuple:
    return {
        'slow': (0, 89),
        'medium': (90, 120),
        'fast': (121, 300)
    }.get(tempo_category.lower(), (0, 300))

def fuzzy_match_artist_song(df, query: str):
    if not isinstance(query, str):
        return df.head(5)

    query = query.lower()
    df['track_artist'] = df['track_artist'].fillna("").astype(str).str.lower()
    df['track_name'] = df['track_name'].fillna("").astype(str).str.lower()

    exact_artist_matches = df[df['track_artist'].str.contains(query, case=False, na=False)]
    if not exact_artist_matches.empty:
        return exact_artist_matches

    exact_song_matches = df[df['track_name'].str.contains(query, case=False, na=False)]
    if not exact_song_matches.empty:
        return exact_song_matches

    if "valence" in df.columns and "energy" in df.columns and "danceability" in df.columns:
        target_song = df[df['track_name'] == query]
        if not target_song.empty:
            target_features = target_song[["valence", "energy", "danceability"]].iloc[0].values
            df["similarity"] = cosine_similarity(
                [target_features], df[["valence", "energy", "danceability"]].values
            ).flatten()
            return df.sort_values(by="similarity", ascending=False).head(5)

    fallback = df.nlargest(5, 'track_popularity') if 'track_popularity' in df.columns else df.head(5)
    return fallback

def generate_chat_response(song_dict: dict, preferences: dict, api_key: str, custom_prompt: str = None) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = custom_prompt or f"""
The user likes {preferences.get('genre', 'some genre')} music, is feeling {preferences.get('mood', 'some mood')}, and prefers {preferences.get('tempo', 'any')} tempo.
Suggest a song that fits: "{song_dict['song']}" by {song_dict['artist']} ({song_dict['genre']}, {song_dict['tempo']} tempo).
Respond in a casual, friendly tone and say why it's a good fit in 1–2 sentences.
"""

    body = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You are a helpful music recommendation assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 250
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=body)
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("Groq Chat Error:", e)
        return f"Here's a great track: '{song_dict['song']}' by {song_dict['artist']}."

def extract_preferences_from_message(message: str, api_key: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are an AI that extracts music preferences from user input.
Respond only in valid JSON with 4 keys: genre, mood, tempo, artist_or_song.
If a value is not explicitly or implicitly stated, use null.

Examples:
- "I love Taylor Swift" → artist_or_song: "Taylor Swift"
- "Play something by Ed Sheeran" → artist_or_song: "Ed Sheeran"
- "I'm in a sad mood" → mood: "sad"
- "Play fast pop music" → tempo: "fast", genre: "pop"
- "Can you recommend a song by Adele?" → artist_or_song: "Adele"

Message: "{message}"
"""

    body = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You extract music preferences from user messages in JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 250
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=body)
        text = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(text[text.index("{"):text.rindex("}")+1])
        for key in ["genre", "mood", "tempo", "artist_or_song"]:
            if key not in parsed:
                parsed[key] = None
        return parsed
    except Exception as e:
        print("Groq Extraction Error:", e)
        return {"genre": None, "mood": None, "tempo": None, "artist_or_song": None}

def map_free_text_to_mood(text: str) -> str:
    text = text.lower()
    if any(word in text for word in ["cry", "sad", "lonely", "depressed", "rainy", "tears"]):
        return "sad"
    elif any(word in text for word in ["party", "hyped", "dance", "workout", "pump", "intense"]):
        return "energetic"
    elif any(word in text for word in ["chill", "calm", "relax", "study", "lofi", "smooth"]):
        return "calm"
    elif any(word in text for word in ["happy", "joy", "sunny", "fun", "good mood"]):
        return "happy"
    return "calm"

def split_mode_category(mode_category: str) -> tuple:
    if isinstance(mode_category, str):
        parts = re.split(r'[\s_]+', mode_category.strip())
        return (parts[0].lower(), parts[1].lower()) if len(parts) >= 2 else (parts[0].lower(), None)
    return (None, None)

def build_recommendation_key(genre: str, mood: str, energy: str, tempo: str) -> str:
    return f"{genre}_{mood.capitalize()} {energy.capitalize()}_{tempo.capitalize()}"

def precompute_recommendation_map(df: pd.DataFrame) -> dict:
    index_map = {}
    for _, row in df.iterrows():
        genre = row.get("playlist_genre", "unknown")
        tempo = row.get("tempo_category", "medium")
        mood, energy = split_mode_category(row.get("mode_category", "calm calm"))
        key = build_recommendation_key(genre, mood, energy, tempo)
        index_map.setdefault(key, []).append(row)
    return index_map
