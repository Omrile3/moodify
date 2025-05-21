import difflib
import requests
import json

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

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
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    prompt = custom_prompt or f"""
The user likes {preferences.get('genre', 'some genre')} music, is feeling {preferences.get('mood', 'some mood')}, and prefers {preferences.get('tempo', 'any')} tempo.

Suggest a song and explain why it fits:
"{song_dict['song']}" by {song_dict['artist']} ({song_dict['genre']}, {song_dict['tempo']} tempo)
"""

    body = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 256,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(CLAUDE_API_URL, headers=headers, json=body)
    try:
        return response.json()['content'][0]['text'].strip()
    except Exception as e:
        print("Claude Error:", e)
        return f"Here's a great track: '{song_dict['song']}' by {song_dict['artist']}."

def extract_preferences_from_message(message: str, api_key: str) -> dict:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    prompt = f"""
Extract music preferences from this message in JSON format: genre, mood, tempo, artist_or_song.
Use lowercase. Use null if not mentioned.

User input: "{message}"
"""

    body = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 256,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(CLAUDE_API_URL, headers=headers, json=body)
        content = response.json()['content'][0]['text']
        parsed = json.loads(content)
        for key in ["genre", "mood", "tempo", "artist_or_song"]:
            if key not in parsed:
                parsed[key] = None
        return parsed
    except Exception as e:
        print("Extraction error:", e)
        return {
            "genre": None, "mood": None, "tempo": None, "artist_or_song": None
        }
