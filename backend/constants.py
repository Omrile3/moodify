"""Constants for the recommendation engine."""

# Preference related constants
PREFERENCE_FIELDS = ["genre", "mood", "tempo", "artist_or_song"]

GENRES = {
    "pop", "rock", "classical", "jazz", "metal", "electronic", 
    "hip hop", "rap", "r&b", "lofi", "latin", "folk", 
    "reggae", "country", "blues", "indie"
}

MOODS = {
    "happy", "sad", "energetic", "calm", "nostalgic", "romantic",
    "angry", "hopeful", "mellow", "funky", "anxious", "relaxed",
    "bittersweet", "uplifting", "melancholy", "dreamy", "groovy",
    "chilled", "moody", "dark", "powerful", "rebellious", "relaxing",
    "intense", "soulful", "epic", "bright", "mysterious", "passionate",
    "sensual", "tropical", "atmospheric", "playful", "fierce", "gritty",
    "peaceful", "chill", "smooth", "melancholic"
}

NO_PREF_WORDS = {
    "no", "none", "nah", "not really", "nothing", "any", 
    "anything", "whatever", "doesn't matter", "does not matter", 
    "no preference", "up to you", "anything is fine", "i don't care", 
    "i don't mind", "doesn't matter to me", "no specific preference"
}

# Mood related constants
SAD_MOODS = {"sad", "melancholy", "down", "emotional", "blue", "heartbreak", "gloomy"}
HAPPY_MOODS = {"happy", "joy", "energetic", "upbeat", "party", "celebrate", "excited"}
UPBEAT_WORDS = {"upbeat", "party", "dance", "energetic", "celebrate", "hyped", "intense"}
SLOW_WORDS = {"slow", "ballad", "chill", "calm"}

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

# Tempo related constants
TEMPO_RANGES = {
    'slow': (0, 89),
    'medium': (90, 120),
    'fast': (121, 300)
}

# API related constants
API_SETTINGS = {
    'OPENAI_MODEL': 'gpt-4o',
    'OPENAI_API_URL': 'https://api.openai.com/v1/chat/completions'
}

# UI related constants
BUTTONS_HTML = """
<br>
<div style='margin-top:10px;display:flex;gap:8px;flex-wrap:wrap'>
    <button onclick="window.handleBotReply('yes')">👍 Yes, I love it!</button>
    <button onclick="window.handleBotReply('no')">🔄 Recommend another</button>
    <button onclick="window.handleBotReply('change mood')">Change mood</button>
    <button onclick="window.handleBotReply('change genre')">Change genre</button>
    <button onclick="window.handleBotReply('change artist')">Change artist</button>
    <button onclick="window.handleBotReply('change tempo')">Change tempo</button>
</div>
"""

# Command types for user feedback
POSITIVE_FEEDBACK = {"yes", "love", "liked", "good", "great", "perfect", "awesome", "sure"}
NEGATIVE_FEEDBACK = {"no", "didn't", "not really", "did not", "nah", "not a good fit", "not fit", "try again"}
CHANGE_COMMANDS = {"change", "switch", "new"}

# Song recommendation categories
SAD_MOODS = {"sad", "melancholy", "down", "emotional", "blue", "heartbreak", "gloomy"}
HAPPY_MOODS = {"happy", "joy", "energetic", "upbeat", "party", "celebrate", "excited"}
UPBEAT_WORDS = {"upbeat", "party", "dance", "energetic", "celebrate", "hyped", "intense"}
SLOW_WORDS = {"slow", "ballad", "chill", "calm"}

# Similarity detection keywords
SIMILARITY_KEYWORDS = {
    "similar to", "like", "vibe like", "in the style of",
    "another artist like", "by a similar artist", "reminiscent of", 
    "same vibe as", "any artist"
}

# Scoring weights for recommendation engine
SCORE_WEIGHTS = {
    "genre_match": 8,
    "mood_match": 8,
    "tempo_match": 8,
    "artist_match": 2,
    "popularity": 1,
    "mood_mismatch": -10,
    "tempo_mismatch": -5
}

# Data paths
DATA_PATH = "data/songs.csv"

# Features for recommendation engine
AUDIO_FEATURES = ['valence', 'energy', 'danceability', 'acousticness', 'tempo']
