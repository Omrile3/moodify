import difflib
import requests
import json
import re
import pandas as pd

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def convert_tempo_to_bpm(tempo_category: str) -> tuple:
    return {
        'slow': (0, 89),
        'medium': (90, 120),
        'fast': (121, 300)
    }.get(tempo_category.lower(), (0, 300))

def fuzzy_match_artist_song(df, query: str):
    if not isinstance(query, str):
        print(f"Invalid query type: {type(query)}. Expected a string.")
        return df.head(5)  # Return top 5 rows as a fallback

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

    # Use fallbacks to avoid saying 'None' in the prompt
    genre = preferences.get('genre') or "any"
    mood = preferences.get('mood') or "any"
    tempo = preferences.get('tempo') or "any"
    song = song_dict.get('song', 'Unknown')
    artist = song_dict.get('artist', 'Unknown')
    song_genre = song_dict.get('genre', 'Unknown')
    song_tempo = song_dict.get('tempo', 'Unknown')

    prompt = custom_prompt or f"""
The user likes {genre} music, is feeling {mood}, and prefers {tempo} tempo.
Suggest a song that fits: "{song}" by {artist} ({song_genre}, {song_tempo} tempo).
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
        return f"Here's a great track: '{song}' by {artist}."

def extract_preferences_from_message(message: str, api_key: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
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
        parsed = json.loads(text[text.index("{"):text.rindex("}")+1])
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
    if any(word in text for word in ["cry", "sad", "lonely", "depressed", "rainy", "tears"]):
        return "sad"
    elif any(word in text for word in ["party", "hyped", "dance", "workout", "pump", "intense"]):
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
