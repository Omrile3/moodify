from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv

from recommender import recommend_song
from memory import SessionMemory
from utils import generate_chat_response, extract_preferences_from_message

# Load .env and OpenAI key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()
memory = SessionMemory()

# CORS
origins = [
    "https://moodify-frontend-cheh.onrender.com",
    "http://localhost:3000",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class PreferenceInput(BaseModel):
    session_id: str
    genre: str = None
    mood: str = None
    tempo: str = None
    artist_or_song: str = None

class CommandInput(BaseModel):
    session_id: str
    command: str

@app.post("/recommend")
def recommend(preference: PreferenceInput):
    user_message = preference.artist_or_song or ""

    # 👋 Greetings & empty input
    if user_message.strip() == "" or any(word in user_message.lower() for word in [
        "hello", "hi", "start", "hey", "who are you", "what can you do","hello!","hey!","hi!","hi there!","hello there!","hey there!","what's up?","how are you?","how's it going?","howdy!","greetings!","salutations!","yo!","sup?","what's new?","what's happening?","what's good?","what's cooking?","what's cracking?","what's popping?","what's the word?","what's the deal?","what's the scoop?"
    ]):
        return {
            "message": (
                "Hey! I'm Moodify — your GPT-powered music buddy 🎧. "
                "Tell me how you feel, what you're into, or name a favorite artist or vibe. "
                "For example: 'Give me a chill acoustic track like Ed Sheeran'."
            ),
            "options": ["I'm sad", "Play pop", "Show me EDM", "Feeling energetic"]
        }

    # 🧠 Extract intent using GPT
    extracted = extract_preferences_from_message(user_message, OPENAI_API_KEY)

    if not extracted:
        return {
            "message": (
                "Hmm, I couldn't understand that. Try telling me a mood, genre, artist, or vibe! "
                "For example: 'I need something calm and romantic'."
            ),
            "options": ["Chill pop", "Fast EDM", "Sad indie", "Latin mood", "Top 5 popular songs"]
        }

    # 🧪 Check if at least one key exists
    if not any(extracted.get(k) for k in ["genre", "mood", "tempo", "artist_or_song"]):
        return {
            "message": (
                "I couldn’t pick out any music preferences from that. "
                "Tell me a genre (like rock), a mood (like sad), tempo, or an artist!"
            ),
            "options": ["Upbeat pop", "Moody rock", "Slow acoustic", "Something by Rihanna", "Popular tracks"]
        }

    # 💾 Update session memory
    session = memory.get_session(preference.session_id)
    for key in ['genre', 'mood', 'tempo', 'artist_or_song']:
        value = extracted.get(key)
        if value:
            memory.update_session(preference.session_id, key, value)

    current_prefs = memory.get_session(preference.session_id)

    # 🎵 Get song recommendation
    song = recommend_song(current_prefs)

    if not song:
        return {
            "message": (
                "Couldn't find anything matching that. Try another artist or vibe!"
            ),
            "options": ["Try pop", "Pick a mood", "Another suggestion"]
        }

    # 🗣️ GPT-style friendly reply
    gpt_message = generate_chat_response(song, current_prefs, OPENAI_API_KEY)

    return {
        "song": song,
        "response": gpt_message,
        "options": ["Another one", "Change genre", "Feeling different"]
    }

@app.post("/command")
def handle_command(command_input: CommandInput):
    cmd = command_input.command.lower()
    session_id = command_input.session_id

    if "another" in cmd:
        prefs = memory.get_session(session_id)
        song = recommend_song(prefs)
        gpt_message = generate_chat_response(song, prefs, OPENAI_API_KEY)
        return {"song": song, "response": gpt_message}

    elif "change" in cmd:
        if "genre" in cmd:
            memory.update_session(session_id, "genre", None)
            return {"message": "Which genre would you like now?"}
        elif "mood" in cmd:
            memory.update_session(session_id, "mood", None)
            return {"message": "What mood are you in?"}
        elif "tempo" in cmd:
            memory.update_session(session_id, "tempo", None)
            return {"message": "What tempo do you prefer? (slow, medium, fast)"}

    return {"message": "I didn’t understand that. Try 'Change genre' or 'Another one'."}

@app.get("/session/{session_id}")
def get_session(session_id: str):
    return memory.get_session(session_id)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
