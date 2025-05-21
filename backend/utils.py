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
        return df  # fallback if no close match

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
        return f"Here's a great song: '{song_dict['song']}' by {song_dict['artist']}."

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
            return parsed if isinstance(parsed, dict) else {}
        else:
            return {}
    except Exception as e:
        print("Extraction error:", e)
        return {}
