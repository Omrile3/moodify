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

# Load Claude API key
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

app = FastAPI()
memory = SessionMemory()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://moodify-frontend-cheh.onrender.com",
        "http://localhost:3000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    if user_message.strip().lower() in ["hello", "hi", "hey", "yo", "start", "what can you do", "who are you"]:
        return {
            "response": "🟢 <span style='color:green'>Hey! I'm <strong>Moodify</strong> 🎧 — your music assistant powered by Claude 3. Tell me how you feel, a favorite artist, or a vibe, and I’ll find a song for you.</span>"
        }

    extracted = extract_preferences_from_message(user_message, ANTHROPIC_API_KEY)

    if not extracted or not any(extracted.values()):
        clarification_prompt = f"""
        The user said: "{user_message}"
        They are asking for a song, but they didn’t provide genre, mood, tempo, or artist.
        Respond in a helpful, friendly tone asking for more information — such as how they feel, genre they like, or a favorite artist.
        """
        gpt_message = generate_chat_response(
            {"song": "N/A", "artist": "N/A", "genre": "N/A", "tempo": "N/A"},
            {"genre": None, "mood": None, "tempo": None},
            ANTHROPIC_API_KEY,
            custom_prompt=clarification_prompt
        )
        return {"response": f"🟢 <span style='color:green'>{gpt_message}</span>"}

    session = memory.get_session(preference.session_id)
    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        value = extracted.get(key)
        if value:
            memory.update_session(preference.session_id, key, value)

    prefs = memory.get_session(preference.session_id)
    song = recommend_song(prefs)

    if not song:
        return {
            "response": "🟢 <span style='color:green'>Hmm... I couldn’t find a great match. Maybe try a different artist or mood?</span>"
        }

    gpt_message = generate_chat_response(song, prefs, ANTHROPIC_API_KEY)
    return {"response": f"🟢 <span style='color:green'>{gpt_message}</span>"}

@app.post("/command")
def handle_command(command_input: CommandInput):
    cmd = command_input.command.lower()
    session_id = command_input.session_id

    if "another" in cmd:
        prefs = memory.get_session(session_id)
        song = recommend_song(prefs)
        gpt_message = generate_chat_response(song, prefs, ANTHROPIC_API_KEY)
        return {"response": f"🟢 <span style='color:green'>{gpt_message}</span>"}

    elif "change" in cmd:
        for key in ["genre", "mood", "tempo"]:
            if key in cmd:
                memory.update_session(session_id, key, None)
                return {"response": f"🟢 <span style='color:green'>What {key} would you like now?</span>"}

    return {"response": "🟢 <span style='color:green'>I didn’t get that. Try 'another one' or 'change genre'.</span>"}

@app.get("/session/{session_id}")
def get_session(session_id: str):
    return memory.get_session(session_id)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
