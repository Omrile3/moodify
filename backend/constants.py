"""Constants for the recommendation engine."""

# API related constants
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o"

# Preference related constants
PREFERENCE_FIELDS = ["genre", "mood", "tempo", "artist_or_song"]

GENRES = {
    "pop", "rock", "classical", "jazz", "metal", "edm", 
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

NO_PREF = "no preference"

NO_PREF_WORDS = {
    "no", "nah", "not really", "nothing", "any", 
    "anything", "whatever", "doesn't matter", "does not matter", 
    "no preference", "up to you", "anything is fine", "i don't care", 
    "i don't mind", "doesn't matter to me", "no specific preference"
}

# Mood vectors for recommendation engine
HARDCODED_MOOD_VECTORS = {
    "happy":        [0.9, 0.8, 0.7, 0.2, 0.6],
    "sad":          [0.2, 0.3, 0.2, 0.6, 0.4],
    "energetic":    [0.7, 0.9, 0.8, 0.1, 0.8],
    "calm":         [0.5, 0.4, 0.3, 0.7, 0.5],
    "nostalgic":    [0.6, 0.4, 0.5, 0.5, 0.4],
    "romantic":     [0.8, 0.5, 0.7, 0.6, 0.5],
    "angry":        [0.3, 0.95, 0.5, 0.1, 0.9],
    "hopeful":      [0.85, 0.6, 0.7, 0.4, 0.6],
    "mellow":       [0.7, 0.3, 0.4, 0.8, 0.3],
    "funky":        [0.8, 0.7, 0.95, 0.3, 0.7],
    "anxious":      [0.3, 0.7, 0.5, 0.2, 0.8],
    "relaxed":      [0.8, 0.4, 0.5, 0.8, 0.4],
    "bittersweet":  [0.6, 0.5, 0.4, 0.6, 0.4],
    "uplifting":    [0.85, 0.75, 0.6, 0.2, 0.7],
    "melancholy":   [0.3, 0.4, 0.4, 0.6, 0.3],
    "dreamy":       [0.7, 0.5, 0.6, 0.7, 0.4],
    "groovy":       [0.8, 0.6, 0.95, 0.2, 0.6],
    "chilled":      [0.6, 0.3, 0.4, 0.9, 0.3],
    "moody":        [0.4, 0.5, 0.5, 0.7, 0.4],
    "dark":         [0.2, 0.7, 0.3, 0.3, 0.7],
    "powerful":     [0.7, 0.95, 0.7, 0.1, 0.8],
    "rebellious":   [0.4, 0.9, 0.7, 0.1, 0.85],
    "relaxing":     [0.8, 0.3, 0.5, 0.8, 0.3],
    "intense":      [0.5, 0.97, 0.6, 0.05, 0.95],
    "soulful":      [0.85, 0.6, 0.8, 0.5, 0.55],
    "epic":         [0.7, 0.95, 0.5, 0.1, 0.95],
    "bright":       [0.9, 0.7, 0.7, 0.3, 0.6],
    "mysterious":   [0.3, 0.4, 0.3, 0.6, 0.4],
    "passionate":   [0.8, 0.85, 0.7, 0.2, 0.7],
    "sensual":      [0.7, 0.6, 0.7, 0.7, 0.5],
    "tropical":     [0.8, 0.7, 0.95, 0.1, 0.7],
    "atmospheric":  [0.5, 0.5, 0.5, 0.9, 0.4],
    "playful":      [0.8, 0.7, 0.8, 0.3, 0.7],
    "fierce":       [0.5, 1.0, 0.5, 0.1, 0.9],
    "gritty":       [0.3, 0.8, 0.7, 0.2, 0.7],
    "peaceful":     [0.9, 0.2, 0.4, 0.95, 0.3],
    "chill":        [0.7, 0.3, 0.5, 0.9, 0.3],
    "smooth":       [0.8, 0.4, 0.8, 0.85, 0.5],
    "melancholic":  [0.4, 0.4, 0.3, 0.7, 0.3],
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
    "great": "happy",
    "bad": "sad",
    "negative": "sad",
    "something bad": "sad",
    "something happy": "happy",
    "uplifting": "happy",
    "something fun": "happy",
    "something sad": "sad",
    "more energy": "energetic",
    "energy": "energetic",
    "energetic": "energetic",
    "calm": "calm",
    "chill": "chill",
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

# Command types for user feedback
POSITIVE_FEEDBACK = {"yes", "love", "liked", "good", "great", "perfect", "awesome", "sure"}
NEGATIVE_FEEDBACK = {"no", "didn't", "not really", "did not", "nah", "not a good fit", "not fit", "try again"}
CHANGE_COMMANDS = {"change", "switch", "new"}

# Song recommendation categories
SAD_MOODS = {"sad", "melancholy", "down", "emotional", "blue", "heartbreak", "gloomy"}
HAPPY_MOODS = {"happy", "joy", "energetic", "upbeat", "party", "celebrate", "excited"}
UPBEAT_WORDS = {"upbeat", "party", "dance", "energetic", "celebrate", "hyped", "intense"}
SLOW_WORDS = {"slow", "ballad", "chill", "calm", "relaxing", "laid-back", "mellow", "soothing", "relax"}

# Similarity detection keywords
SIMILARITY_KEYWORDS = {
    "similar to", "like", "vibe like", "in the style of",
    "another artist like", "by a similar artist", "reminiscent of", 
    "same vibe as", "any artist"
}

# Scoring weights for recommendation engine
SCORE_WEIGHTS = {
    "genre_match": 10,
    "mood_match": 10,
    "tempo_match": 8,
    "artist_match": 2,
    "popularity": 1,
    "mood_mismatch": -5,
    "tempo_mismatch": -5
}

# Data paths
DATA_PATH = "data/songs.csv"

# Features for recommendation engine
AUDIO_FEATURES = ['valence', 'energy', 'danceability', 'acousticness', 'tempo']
