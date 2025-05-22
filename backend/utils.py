import difflib
import requests
import json

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def convert_tempo_to_bpm(tempo_category: str) -> tuple:
    return {
        'slow': (0, 89),
        'medium': (90, 120),
        'fast': (121, 300)
    }.get(tempo_category.lower(), (0, 300))

def fuzzy_match_artist_song(df, query: str):
    query = query.lower()
    artist_matches = difflib.get_close_matches(query, df['track_artist'].str.lower(), n=5, cutoff=0.6)
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
Output: {"genre": null, "mood": "happy", "tempo": "fast", "artist_or_song": "Dua Lipa"}

Input: "{message}"
"""


    body = {
        "model": "mixtral-8x7b-32768",
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
        "model": "mixtral-8x7b-32768",
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

