import difflib
import openai

# Tempo range translator
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

# Fuzzy match artist or song from dataset
def fuzzy_match_artist_song(df, query: str):
    query = query.lower()
    artist_matches = difflib.get_close_matches(query, df['track_artist'].str.lower(), n=5, cutoff=0.6)
    song_matches = difflib.get_close_matches(query, df['track_name'].str.lower(), n=5, cutoff=0.6)

    if artist_matches:
        return df[df['track_artist'].str.lower().isin(artist_matches)]
    elif song_matches:
        return df[df['track_name'].str.lower().isin(song_matches)]
    else:
        return df  # fallback to unfiltered

# Generate natural GPT-style message
def generate_chat_response(song_dict: dict, preferences: dict, api_key: str) -> str:
    openai.api_key = api_key

    prompt = f"""
    The user likes {preferences.get('genre', 'some genre')} music, is feeling {preferences.get('mood', 'a certain mood')}, and prefers {preferences.get('tempo', 'any')} tempo.

    Suggest a song that fits their taste in a friendly tone. Add one sentence why it fits.

    Song to suggest:
    "{song_dict['song']}" by {song_dict['artist']} ({song_dict['genre']}, {song_dict['tempo']} tempo).
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Or gpt-4 if available
            messages=[
                {"role": "system", "content": "You are a helpful music recommendation assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Here's a great song for you: '{song_dict['song']}' by {song_dict['artist']}."

