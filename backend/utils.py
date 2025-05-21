import difflib
import openai

# 🎚️ Convert user tempo to BPM range
def convert_tempo_to_bpm(tempo_category: str) -> tuple:
    tempo_category = tempo_category.lower()
    return {
        'slow': (0, 89),
        'medium': (90, 120),
        'fast': (121, 300)
    }.get(tempo_category, (0, 300))

# 🎯 Match artist or track by fuzzy text
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

# 🧠 GPT-powered response generation
def generate_chat_response(song_dict: dict, preferences: dict, api_key: str) -> str:
    openai.api_key = api_key

    prompt = f"""
    The user likes {preferences.get('genre', 'some genre')} music, is feeling {preferences.get('mood', 'some mood')}, and prefers {preferences.get('tempo', 'any')} tempo.

    Suggest a song in a fun, helpful tone. Explain in one line why this song fits.

    Song: "{song_dict['song']}" by {song_dict['artist']} ({song_dict['genre']}, {song_dict['tempo']} tempo)
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You're Moodify, a chill and friendly music recommendation assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception:
        return (
            f"Here's a great track: '{song_dict['song']}' by {song_dict['artist']} — "
            f"a perfect fit for your vibe!"
        )

# 📦 Extract music preferences using GPT (super NLP)
def extract_preferences_from_message(message: str, api_key: str) -> dict:
    openai.api_key = api_key

    prompt = f"""
    From this message, extract music preferences in lowercase JSON format with keys: genre, mood, tempo, artist_or_song.
    Use null for anything not mentioned.

    Message: "{message}"
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Extract music preferences from casual human messages."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        content = response['choices'][0]['message']['content']
        if "{" in content:
            start = content.index("{")
            end = content.rindex("}") + 1
            parsed = eval(content[start:end])
            for key in ["genre", "mood", "tempo", "artist_or_song"]:
                if key not in parsed:
                    parsed[key] = None
            return parsed
        return {}
    except Exception as e:
        print("Extraction error:", e)
        return {
            "genre": None, "mood": None, "tempo": None, "artist_or_song": None
        }
