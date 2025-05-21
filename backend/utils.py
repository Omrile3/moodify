import difflib
import openai

# Convert tempo label to BPM range
def convert_tempo_to_bpm(tempo_category: str) -> tuple:
    tempo_category = tempo_category.lower()
    if tempo_category == 'slow':
        return (0, 89)
    elif tempo_category == 'medium':
        return (90, 120)
    elif tempo_category == 'fast':
        return (121, 300)
    else:
        return (0, 300)

# Match similar artist or song from the dataset
def fuzzy_match_artist_song(df, query: str):
    query = query.lower()
    artist_matches = difflib.get_close_matches(query, df['track_artist'].str.lower(), n=5, cutoff=0.6)
    song_matches = difflib.get_close_matches(query, df['track_name'].str.lower(), n=5, cutoff=0.6)

    if artist_matches:
        return df[df['track_artist'].str.lower().isin(artist_matches)]
    elif song_matches:
        return df[df['track_name'].str.lower().isin(song_matches)]
    else:
        # Enhanced fallback: Return top 5 songs by popularity as a default
        return df.nlargest(5, 'popularity') if 'popularity' in df.columns else df.head(5)

# 🎤 Chat-like response using GPT
def generate_chat_response(song_dict: dict, preferences: dict, api_key: str) -> str:
    openai.api_key = api_key

    prompt = f"""
    The user likes {preferences.get('genre', 'some genre')} music, is feeling {preferences.get('mood', 'a certain mood')}, and prefers {preferences.get('tempo', 'any')} tempo.

    Suggest a song that fits their taste in a friendly tone. Add one sentence explaining why you chose it.

    Song:
    "{song_dict['song']}" by {song_dict['artist']} ({song_dict['genre']}, {song_dict['tempo']} tempo).
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful music recommendation assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception:
        # Enhanced fallback response
        fallback_message = (
            f"I couldn't generate a detailed response right now, but here's a great song: "
            f"'{song_dict['song']}' by {song_dict['artist']} ({song_dict['genre']}, {song_dict['tempo']} tempo). "
            "It's a fantastic choice based on your preferences!"
        )
        return fallback_message

# 🧠 GPT-based preference extractor
def extract_preferences_from_message(message: str, api_key: str) -> dict:
    openai.api_key = api_key

    prompt = f"""
    From the following message, extract musical preferences in JSON format with keys: genre, mood, tempo, artist_or_song.
    Use null if not specified. Keep keys lowercase.

    Message: "{message}"
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You extract music preferences from user input."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7)

        # Attempt to safely parse response content
        content = response['choices'][0]['message']['content']
        if "{" in content:
            start = content.index("{")
            end = content.rindex("}") + 1
            parsed = eval(content[start:end])
        if isinstance(parsed, dict):
            # Fill missing keys with None to ensure all preferences are present
            for key in ["genre", "mood", "tempo", "artist_or_song"]:
                if key not in parsed:
                    parsed[key] = None
            return parsed
        return {}
    except Exception as e:
        print("Extraction error:", e)

        # Fallback: Basic keyword-based extraction
        keywords = {
            "genre": ["pop", "rock", "jazz", "classical", "hip-hop", "edm", "indie"],
            "mood": ["happy", "sad", "energetic", "calm", "romantic", "angry"],
            "tempo": ["slow", "medium", "fast"],
        }
        extracted = {key: None for key in ["genre", "mood", "tempo", "artist_or_song"]}
        for key, values in keywords.items():
            for value in values:
                if value in message.lower():
                    extracted[key] = value
                    break
        return extracted
