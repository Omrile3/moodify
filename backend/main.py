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

# Load OpenAI API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()
memory = SessionMemory()

# CORS setup
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

    # 🟢 Handle greeting & intro
    greetings = [
        "hello", "hi", "start", "hey", "who are you", "what can you do",
        "hello!", "hi!", "hi there!", "yo!", "sup?", "what’s up"
    ]
    if user_message.strip().lower() in greetings:
        return {
            "message": (
                "🟢 <span style='color:green'>Hey! I'm <strong>Moodify</strong> — your GPT-powered music buddy 🎧.</span><br>"
                "Tell me how you feel, your favorite vibe, or an artist — and I’ll find the perfect song."
            ),
            "options": ["I'm sad", "Play pop", "Feeling energetic", "Show me EDM"]
        }

    # 🧠 Extract user preferences with GPT
    extracted = extract_preferences_from_message(user_message, OPENAI_API_KEY)

    # ❓ If nothing usable, guide user
    if not extracted or not any(extracted.values()):
        return {
            "message": (
                "🟢 <span style='color:green'>Hmm... I couldn't extract enough to recommend a song.</span><br>"
                "Tell me a genre, a mood, or an artist — like 'play something chill by Coldplay'."
            ),
            "options": ["Happy mood", "Rock artist", "Fast track", "Something emotional"]
        }

    # 🔎 If partial info → follow-up questions
    missing_keys = [k for k in ["genre", "mood", "tempo", "artist_or_song"] if not extracted.get(k)]
    if missing_keys:
        questions = {
            "genre": "What genre do you like? (pop, rock, jazz...)",
            "mood": "How are you feeling? (happy, sad, energetic...)",
            "tempo": "What tempo do you prefer? (slow, medium, fast)",
            "artist_or_song": "Any favorite artist or song in mind?"
        }
        return {
            "message": "🟢 <span style='color:green'>Got it! But I need a bit more info:</span>",
            "follow_up_questions": [questions[k] for k in missing_keys]
        }

    # 💾 Update session memory
    session = memory.get_session(preference.session_id)
    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        val = extracted.get(key)
        if val:
            memory.update_session(preference.session_id, key, val)

    prefs = memory.get_session(preference.session_id)

    # 🎧 Get recommendation
    song = recommend_song(prefs)
    if not song:
        return {
            "message": (
                "🟢 <span style='color:green'>Sorry, couldn't find a good match. Want to try something else?</span>"
            ),
            "options": ["Try another genre", "Suggest again", "Change artist"]
        }

    # 🗣️ GPT chat-style reply
    gpt_message = generate_chat_response(song, prefs, OPENAI_API_KEY)

    return {
        "song": song,
        "response": f"🟢 <span style='color:green'>{gpt_message}</span>",
        "options": ["Another one", "Change mood", "Feeling different"]
    }

@app.post("/command")
def handle_command(command_input: CommandInput):
    cmd = command_input.command.lower()
    session_id = command_input.session_id

    if "another" in cmd:
        prefs = memory.get_session(session_id)
        song = recommend_song(prefs)
        gpt_message = generate_chat_response(song, prefs, OPENAI_API_KEY)
        return {"song": song, "response": f"🟢 <span style='color:green'>{gpt_message}</span>"}

    elif "change" in cmd:
        for k in ["genre", "mood", "tempo"]:
            if k in cmd:
                memory.update_session(session_id, k, None)
                return {"message": f"🟢 <span style='color:green'>What {k} would you like now?</span>"}

    return {"message": "🟢 <span style='color:green'>I didn’t get that. Try saying 'another one' or 'change mood'.</span>"}

@app.get("/session/{session_id}")
def get_session(session_id: str):
    return memory.get_session(session_id)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
