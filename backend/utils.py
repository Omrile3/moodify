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
Suggest a great song: "{song_dict['song']}" by {song_dict['artist']} ({song_dict['genre']}, {song_dict['tempo']} tempo)
Explain why it fits their vibe in 1 sentence.
"""

    body = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 256,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(CLAUDE_API_URL, headers=headers, json=body)
        data = response.json()
        if "content" in data and isinstance(data["content"], list):
            return data["content"][0].get("text", "").strip()
        else:
            print("Claude format error:", data)
            return "I had trouble generating a suggestion."
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
Extract music preferences from this message in valid JSON format.
Keys: genre, mood, tempo, artist_or_song. All lowercase. Use null if not present.

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
        data = response.json()

        if "content" in data and isinstance(data["content"], list):
            text = data["content"][0].get("text", "").strip()
        else:
            print("Claude extraction format error:", data)
            return {
                "genre": None, "mood": None, "tempo": None, "artist_or_song": None
            }

        # Parse text block safely into JSON
        if "{" in text and "}" in text:
            parsed = json.loads(text[text.index("{"):text.rindex("}")+1])
        else:
            return {
                "genre": None, "mood": None, "tempo": None, "artist_or_song": None
            }

        # Ensure keys
        for key in ["genre", "mood", "tempo", "artist_or_song"]:
            if key not in parsed:
                parsed[key] = None

        return parsed

    except Exception as e:
        print("Extraction error:", e)
        return {
            "genre": None, "mood": None, "tempo": None, "artist_or_song": None
        }
