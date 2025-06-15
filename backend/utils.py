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

NONE_LIKE = {
    "no", "none", "nah", "not really", "nothing", "any", "anything", "whatever",
    "doesn't matter", "does not matter", "no preference", "up to you",
    "anything is fine", "i don't care", "i don't mind", "doesn't matter to me", "no specific preference", "no prefernce"
}

# --- PATCH: Improved mapping for vague terms ---
VAGUE_TO_MOOD = {
    "something good": "happy",
    "good": "happy",
    "positive": "happy",
    "uplifting": "happy",
    "something fun": "happy",
    "something sad": "sad",
    "more energy": "energetic",
    "energy": "energetic",
    "energetic": "energetic",
    "calm": "calm",
    "chill": "calm",
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
    spotify_url = song_dict.get('spotify_url')

    prompt = custom_prompt or f"""
The user wants a song that matches these preferences:
Genre: {genre}, Mood: {mood}, Tempo: {tempo}.
Recommend only the selected song: "{song}" by {artist} ({song_genre}, {song_tempo} tempo).
Reply in a warm and friendly tone. Your response must be short and concise — no more than 1.5 sentences.
Don't suggest alternatives or explain why. Mention only this one song.
"""

    body = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You are a helpful music assistant. Respond in under 1.5 sentences."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6,
        "max_tokens": 200
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=body)
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]["content"].strip()
        if spotify_url:
            message += f' 🎵 <a href="{spotify_url}" target="_blank">Listen on Spotify</a>'
        return message
    except Exception as e:
        print("Groq Chat Error:", e)
        return f"🎵 Here’s a great track: '{song}' by {artist}." + (f' <a href="{spotify_url}" target="_blank">Listen</a>' if spotify_url else "")

def extract_preferences_from_message(message: str, api_key: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    msg = message.strip().lower()

    # --- PATCH: catch "none/no preference/anything" directly for all fields ---
    def is_none_like(val):
        return val in NONE_LIKE or any(val.strip() == word for word in NONE_LIKE)

    # Try to auto-map vague mood/tempo responses (fast path, pre-LLM)
    mapped = {}
    for phrase, mapped_val in VAGUE_TO_MOOD.items():
        if phrase in msg:
            if mapped_val in {"happy", "sad", "calm", "energetic"}:
                mapped["mood"] = mapped_val
            if mapped_val == "energetic":
                mapped["tempo"] = "fast"
            break

    # "no preference" explicit for each category
    none_fields = {
        "genre": any(term in msg for term in ["no genre", "any genre", "no preference for genre"]),
        "mood": any(term in msg for term in ["no mood", "any mood", "no preference for mood"]),
        "tempo": any(term in msg for term in ["no tempo", "any tempo", "no preference for tempo"]),
        "artist_or_song": any(term in msg for term in ["no artist", "any artist", "no preference for artist", "no favorite artist", "anything"])
    }
    # Also cover general "anything/no preference/whatever" with minimal input
    if any(is_none_like(word) for word in msg.split()):
        if len(msg.split()) <= 3:
            for key in none_fields:
                none_fields[key] = True

    # --- PATCH: Robust LLM call and JSON extraction ---
    extracted = {}
    if not any(none_fields.values()):
        prompt = f"""
You are an AI that extracts music preferences from user input.
Respond only in valid JSON with exactly these 4 keys: genre, mood, tempo, artist_or_song.
If a value is not explicitly or implicitly stated, use null.

If the user mentions a mood like "sad", "happy", "calm", or "energetic", copy that word directly as the mood.
If the user mentions a genre like "indie", "pop", "rock", "jazz", etc., copy that directly as the genre.

Do NOT map or reinterpret "sad" to "calm" or anything else; preserve mood/genre exactly as the user says, unless the user gives a clear synonym ("melancholy" → "sad" is OK).

Examples:
- "I'm feeling sad" → mood: "sad"
- "I like indie music" → genre: "indie"
- "I'm happy and want upbeat pop" → mood: "happy", genre: "pop", tempo: "fast" or "upbeat"

Input: "{message}"
"""
        body = {
            "model": "llama3-70b-8192",
            "messages": [
                {"role": "system", "content": "You extract music preferences from user messages in JSON, copying mood and genre words exactly unless a clear synonym is used. Do NOT reinterpret 'sad' or 'indie'."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 250
        }

        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=body)
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]

            # --- PATCH: Robust JSON extraction ---
            import re
            text = text.strip()
            if text.startswith("```"):
                text = text.lstrip("`")
                text = text[text.find("{"):]
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                json_text = match.group(0)
                try:
                    extracted = json.loads(json_text)
                except Exception as e:
                    print("Groq Extraction Error (inner):", e, "| Offending text:", repr(json_text))
                    extracted = {"genre": None, "mood": None, "tempo": None, "artist_or_song": None}
            else:
                print("Groq Extraction Error: Could not find JSON object in:", repr(text))
                extracted = {"genre": None, "mood": None, "tempo": None, "artist_or_song": None}
        except Exception as e:
            print("Groq Extraction Error:", e)
            extracted = {"genre": None, "mood": None, "tempo": None, "artist_or_song": None}
    else:
        # If any explicit "none", just set them as None
        extracted = {"genre": None, "mood": None, "tempo": None, "artist_or_song": None}

    # --- Patch: overwrite with mapped/none values ---
    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        if none_fields.get(key):
            extracted[key] = None
        if key in mapped and mapped[key]:
            extracted[key] = mapped[key]
        # Always normalize any "none-like" phrases to None
        if extracted.get(key) and extracted[key].strip().lower() in NONE_LIKE:
            extracted[key] = None

    return {k: extracted.get(k, None) for k in ["genre", "mood", "tempo", "artist_or_song"]}


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

def next_ai_message(session: dict, last_user_message: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    known_prefs = []
    for k in ["genre", "mood", "tempo", "artist_or_song"]:
        v = session.get(k)
        if v:
            known_prefs.append(f"{k}: {v}")
    prefs_str = ", ".join(known_prefs) if known_prefs else "none yet"

    # --- PATCH: add no_pref flags info for LLM ---
    no_prefs = []
    for k in ["genre", "mood", "tempo", "artist_or_song"]:
        if session.get(f"no_pref_{k}", False):
            no_prefs.append(k)
    no_pref_str = ", ".join(no_prefs) if no_prefs else "none"

    prompt = f"""
You are Moodify, a helpful, friendly music AI. You are helping a user choose a song.
Here is what you know about the user's preferences so far: {prefs_str}.
User has said they have no preference for: {no_pref_str}.

Recent user message: "{last_user_message}"

If you are still missing genre, mood, tempo, or artist, ask a short (1 line), friendly follow-up question about the next missing thing, unless user said they have no preference for that (don't ask again if so).
When you have enough info, say your recommended song in one concise (one line), enthusiastic sentence, then ask the user if they like it.
genre can be any of: {', '.join(GENRES)}.
mood can be: sad, energetic, calm, happy.
tempo can be: slow, medium, fast.
artist_or_song can be any artist or song name.

- NEVER ask the user the same thing twice or to confirm the same preference repeatedly.
- If you already know at least two out of genre, mood, and tempo, STOP asking clarifying questions and RECOMMEND a song.
- If the user says "yes", "no", or repeats their preference, just move forward or adjust accordingly.
- You may ask up to 2 follow-up questions if mood or genre is still missing, but never repeat yourself.
- After 3 clarifying messages, you must always recommend a song, even if something is missing.
- Do NOT restate the session data, just reply naturally as a chat assistant.

If the user asks to change something, help them do so.

Be as conversational as possible, do not use a fixed script. Reply with only your message, do not restate the session data.
Ask a maximum of 4 questions before recommending a song.
"""
    body = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You are a friendly AI music assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=body)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("Groq next_ai_message error:", e)
        return "What are you in the mood for today?"
