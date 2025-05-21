from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv
from typing import Optional

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
    genre: Optional[str] = None
    mood: Optional[str] = None
    tempo: Optional[str] = None
    artist_or_song: Optional[str] = None

class CommandInput(BaseModel):
    session_id: str
    command: str

@app.post("/recommend")
def recommend(preference: PreferenceInput):
    user_message = preference.artist_or_song or ""

    # 👋 Handle greetings and general conversation
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

    # 🗣️ Handle general conversational input
    if not any(keyword in user_message.lower() for keyword in ["music", "song", "artist", "genre", "mood", "tempo"]):
        gpt_response = generate_chat_response(
            {"song": "N/A", "artist": "N/A", "genre": "N/A", "tempo": "N/A"},
            {"genre": None, "mood": None, "tempo": None},
            OPENAI_API_KEY
        )
        return {
            "message": gpt_response,
            "options": ["Talk about music", "Recommend a song", "Tell me a joke"]
        }

    # � Extract intent using GPT
    extracted = extract_preferences_from_message(user_message, OPENAI_API_KEY)

    if not extracted:
        return {
            "message": (
                "Hmm, I couldn't understand that. Try telling me a mood, genre, artist, or vibe! "
                "For example: 'I need something calm and romantic'."
            ),
            "options": ["Chill pop", "Fast EDM", "Sad indie", "Latin mood", "Top 5 popular songs"]
        }

    # �🧪 Check for missing preferences and prompt user
    missing_keys = [key for key in ["genre", "mood", "tempo", "artist_or_song"] if not extracted.get(key)]
    if missing_keys:
        prompts = {
            "genre": "What genre of music do you like? (e.g., pop, rock, jazz)",
            "mood": "What mood are you in? (e.g., happy, sad, energetic)",
            "tempo": "What tempo do you prefer? (e.g., slow, medium, fast)",
            "artist_or_song": "Do you have a favorite artist or song in mind?"
        }
        follow_up_questions = [prompts[key] for key in missing_keys]
        return {
            "message": "I need a bit more information to find the perfect song for you.",
            "follow_up_questions": follow_up_questions
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
