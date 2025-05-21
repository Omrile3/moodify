from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv

from recommender import recommend_song
from memory import SessionMemory
from utils import generate_chat_response

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()
memory = SessionMemory()

origins = [
    "https://moodify-frontend-cheh.onrender.com",  # your deployed frontend
    "http://localhost:3000",                       # optional: for local dev
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🧾 Data models
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
    session = memory.get_session(preference.session_id)

    # Update session preferences
    for key in ['genre', 'mood', 'tempo', 'artist_or_song']:
        value = getattr(preference, key)
        if value:
            memory.update_session(preference.session_id, key, value)

    current_prefs = memory.get_session(preference.session_id)
    song = recommend_song(current_prefs)

    if not song:
        return {"message": "Sorry, couldn't find a match for your preferences."}

    gpt_message = generate_chat_response(song, current_prefs, OPENAI_API_KEY)

    return {
        "song": song,
        "response": gpt_message,
        "options": ["Want another recommendation?", "Change genre?", "Change mood?"]
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

    return {"message": "Command not understood. Try again."}

@app.get("/session/{session_id}")
def get_session(session_id: str):
    return memory.get_session(session_id)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
