"""Utility functions for the Moodify backend."""

import difflib
import re
import requests
import pandas as pd
from prompts import (
    CHAT_RESPONSE_PROMPT,
    NEXT_MESSAGE_PROMPT,
    NEXT_MESSAGE_USER_PROMPT,
    MOOD_VECTOR_PROMPT,
    SYSTEM_ROLES,
    GPT_SETTINGS
)
from constants import OPENAI_MODEL, OPENAI_API_URL

def fuzzy_match_word(word, options, cutoff=0.75):
    """Find closest match for a word in a set of options."""
    if not word:
        return None
    matches = difflib.get_close_matches(word.lower(), options, n=1, cutoff=cutoff)
    if matches:
        return matches[0]
    return None

def fuzzy_match_artist_song(df, query: str):
    """Find matching artists or songs in the dataset."""
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
    """Generate a chat response for a song recommendation."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Prepare format variables
    format_vars = {
        'genre': preferences.get('genre') or "any",
        'mood': preferences.get('mood') or "any",
        'tempo': preferences.get('tempo') or "any",
        'song': song_dict.get('song', 'Unknown'),
        'artist': song_dict.get('artist', 'Unknown'),
        'song_genre': song_dict.get('genre', 'Unknown'),
        'song_tempo': song_dict.get('tempo', 'Unknown')
    }

    prompt = custom_prompt or CHAT_RESPONSE_PROMPT.format(**format_vars)
    spotify_url = song_dict.get('spotify_url')

    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_ROLES['chat_response']},
            {"role": "user", "content": prompt}
        ],
        **GPT_SETTINGS['chat_response']
    }

    try:
        response = requests.post(
           OPENAI_API_URL,
            headers=headers,
            json=body
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]["content"].strip()
        
        if spotify_url and isinstance(spotify_url, str) and "open.spotify.com/track/" in spotify_url and len(spotify_url) > 35:
            message += f' 🎵 <a href="{spotify_url}" target="_blank">Listen on Spotify</a>'
        return message
    except Exception as e:
        print("OpenAI Chat Error:", e)
        fallback = f"🎵 Here's a great track: '{format_vars['song']}' by {format_vars['artist']}."
        if spotify_url and isinstance(spotify_url, str) and "open.spotify.com/track/" in spotify_url and len(spotify_url) > 35:
            fallback += f' <a href="{spotify_url}" target="_blank">Listen</a>'
        return fallback

def next_ai_message(session: dict, last_user_message: str, api_key: str) -> str:
    """Generate next AI message based on conversation context."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    all_keys = ["genre", "mood", "tempo", "artist_or_song"]
    known_prefs = {k: session.get(k) for k in all_keys if session.get(k) is not None}
    missing = [k for k in all_keys if not (session.get(k) is not None or session.get(f"no_pref_{k}", False))]
    no_prefs = [k for k in all_keys if session.get(f"no_pref_{k}", False)]

    format_vars = {
        'known_prefs': known_prefs,
        'no_prefs': no_prefs,
        'missing': missing,
        'last_user_message': last_user_message
    }

    user_prompt = NEXT_MESSAGE_USER_PROMPT.format(**format_vars)

    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": NEXT_MESSAGE_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        **GPT_SETTINGS['next_message']
    }

    try:
        response = requests.post(
            OPENAI_API_URL,
            headers=headers,
            json=body
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("OpenAI next_ai_message error:", e)
        return "What kind of music do you feel like today?"

def get_mood_vector(mood: str, api_key: str) -> list:
    """Get mood vector for a given mood."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = MOOD_VECTOR_PROMPT.format(mood=mood)

    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_ROLES['mood_vector']},
            {"role": "user", "content": prompt}
        ],
        **GPT_SETTINGS['mood_vector']
    }

    try:
        response = requests.post(
            OPENAI_API_URL,
            headers=headers,
            json=body,
            timeout=10
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"].strip()
        
        # Extract and validate vector
        match = re.search(r"\[([^\[\]]+)\]", text)
        if match:
            arr = match.group(0)
            arr = [float(x.strip()) for x in arr.strip("[]").split(",")]
            if len(arr) == 5 and all(0 <= x <= 1 for x in arr):
                return arr
    except Exception as e:
        print("GPT mood vector fetch failed:", e)
    
    return [0.5, 0.5, 0.5, 0.5, 0.5]  # Neutral fallback

def convert_tempo_to_bpm(tempo_category: str) -> tuple:
    """Convert tempo category to BPM range."""
    return {
        'slow': (0, 89),
        'medium': (90, 120),
        'fast': (121, 300)
    }.get(tempo_category.lower(), (0, 300))

def bpm_to_tempo_category(bpm: float) -> str:
    """Convert BPM to tempo category."""
    if bpm < 90:
        return "slow"
    elif bpm <= 120:
        return "medium"
    else:
        return "fast"

def split_mode_category(mode_category: str) -> tuple:
    """Split mode category into mood and energy components."""
    if isinstance(mode_category, str):
        parts = re.split(r'[\s_]+', mode_category.strip())
        return (parts[0].lower(), parts[1].lower()) if len(parts) >= 2 else (parts[0].lower(), None)
    return (None, None)

def build_recommendation_key(genre: str, mood: str, energy: str, tempo: str) -> str:
    """Build a key for the recommendation map."""
    return f"{genre}_{mood.capitalize()} {energy.capitalize()}_{tempo.capitalize()}"

def precompute_recommendation_map(df: pd.DataFrame) -> dict:
    """Precompute recommendation map for faster lookups."""
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
