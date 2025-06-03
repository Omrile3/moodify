import difflib
import requests
import json
import re
import pandas as pd
import base64
import os

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

GENRES = {
    "pop", "rock", "classical", "jazz", "metal", "electronic", "hip hop", "rap",
    "r&b", "lofi", "latin", "folk", "reggae", "country", "blues", "indie"
}

def convert_tempo_to_bpm(tempo_category: str) -> tuple:
    return {
        'slow': (0, 89),
        'medium': (90, 120),
        'fast': (121, 300)
    }.get(tempo_category.lower(), (0, 300))

def bpm_to_tempo_category(bpm: float) -> str:
    if bpm < 90:
        return "slow"
    elif bpm <= 120:
        return "medium"
    else:
        return "fast"

def fuzzy_match_artist_song(df, query: str):
    if not isinstance(query, str):
        print(f"Invalid query type: {type(query)}. Expected a string.")
        return df.head(5)

    query = query.lower()
    print(f"Performing fuzzy match for query: {query}")
    df['track_artist'] = df['track_artist'].fillna("").astype(str).str.lower()
    df['track_name'] = df['track_name'].fillna("").astype(str).str.lower()

    artist_matches = difflib.get_close_matches(query, df['track_artist'], n=5, cutoff=0.6)
    song_matches = difflib.get_close_matches(query, df['track_name'].str.lower(), n=5, cutoff=0.6)
    if artist_matches:
        return df[df['track_artist'].str.lower().isin(artist_matches)]
    elif song_matches:
        return df[df['track_name'].str.lower().isin(song_matches)]
    else:
        return df.nlargest(5, 'popularity') if 'popularity' in df.columns else df.head(5)

def generate_chat_response(song_dict: dict, preferences: dict, api_key: str, custom_prompt: str = None) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    genre = preferences.get('genre') or "any"
    mood = preferences.get('mood') or "any"
    tempo = preferences.get('tempo') or "any"
    song = song_dict.get('song', 'Unknown')
    artist = song_dict.get('artist', 'Unknown')
    song_genre = song_dict.get('genre', 'Unknown')
    song_tempo = song_dict.get('tempo', 'Unknown')

    # Convert tempo float to category if needed
    if isinstance(song_tempo, (float, int)):
        song_tempo = bpm_to_tempo_category(song_tempo)

    spotify_url = song_dict.get('spotify_url')

    prompt = custom_prompt or f"""
The user asked for a song with the following preferences:
Genre: {genre}, Mood: {mood}, Tempo: {tempo}.
Suggest a song that fits these preferences: "{song}" by {artist} ({song_genre}, {song_tempo} tempo).

Explain briefly (2-3 sentences) in a friendly tone why it's a good fit. only mention the selected song in your reply,
Do not recommend other songs or artists.
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
        message = response.json()["choices"][0]["message"]["content"].strip()
        if spotify_url:
            message += f' 🎵 <a href="{spotify_url}" target="_blank">Listen on Spotify</a>'
        return message
    except Exception as e:
        print("Groq Chat Error:", e)
        return f"Here's a great track: '{song}' by {artist}." + (f' 🎵 <a href="{spotify_url}" target="_blank">Listen</a>' if spotify_url else "")

def extract_preferences_from_message(message: str, api_key: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    lowered = message.lower()
    similarity_phrases = ["similar to", "like", "sounds like", "vibe like", "in the style of", "reminiscent of", "same vibe as", "any artist"]
    for phrase in similarity_phrases:
        if phrase in lowered:
            match = re.search(rf"{phrase} ([\w\s]+)", lowered)
            if match:
                candidate = match.group(1).strip().lower()
                if candidate in GENRES:
                    return {
                        "genre": candidate,
                        "mood": map_free_text_to_mood(message),
                        "tempo": None,
                        "artist_or_song": None
                    }
                return {
                    "genre": None,
                    "mood": map_free_text_to_mood(message),
                    "tempo": None,
                    "artist_or_song": candidate
                }

    prompt = f"""
You are an AI that extracts music preferences from user input.
Respond only in valid JSON with 4 keys: genre, mood, tempo, artist_or_song.
If a value is not explicitly or implicitly stated, use null.

Understand tone and emotion to classify mood:
- "I feel like crying", "it's been a tough day" → "sad"
- "let’s party", "hyped up", "workout music" → "energetic"
- "need to relax", "chill", "lofi", "study" → "calm"
- "sunny day", "good mood", "sing along" → "happy"

Also extract genre (pop, rock, classical, etc.), tempo (slow, medium, fast), or artist/song names.

Example:
Input: "Play something upbeat, I love Dua Lipa."
Output: {{"genre": null, "mood": "happy", "tempo": "fast", "artist_or_song": "Dua Lipa"}}

Input: "{message}"
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
        text = text[text.index("{"):text.rindex("}")+1]
        parsed = json.loads(text)

        # Defensive check
        if parsed["artist_or_song"] and parsed["artist_or_song"].lower() in GENRES:
            parsed["genre"] = parsed["artist_or_song"].lower()
            parsed["artist_or_song"] = None

        for key in ["genre", "mood", "tempo", "artist_or_song"]:
            if key not in parsed:
                parsed[key] = None
        return parsed
    except Exception as e:
        print("Groq Extraction Error:", e)
        return {
            "genre": None, "mood": None, "tempo": None, "artist_or_song": None
        }

def map_free_text_to_mood(text: str) -> str:
    text = text.lower()
    if any(word in text for word in ["cry", "sad", "lonely", "depressed", "rainy", "tears", "tired", "exhausted"]):
        return "sad"
    elif any(word in text for word in ["party", "hyped", "dance", "workout", "pump", "intense", "energetic", "upbeat"]):
        return "energetic"
    elif any(word in text for word in ["chill", "calm", "relax", "study", "lofi", "smooth"]):
        return "calm"
    elif any(word in text for word in ["happy", "joy", "sunny", "fun", "good mood"]):
        return "happy"
    elif any(word in text for word in ["angry", "mad", "rage", "furious", "pissed"]):
        return "energetic"
    else:
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
        if key not in index_map:
            index_map[key] = []
        index_map[key].append(row)
    return index_map
