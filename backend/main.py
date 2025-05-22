from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv
from typing import Optional

from recommender_eng import recommend_engine
from memory import SessionMemory
from utils import generate_chat_response, extract_preferences_from_message

# Load Groq key
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI()
memory = SessionMemory()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporarily allow all origins for testing
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

    greetings = [
        "hello", "hi", "start", "hey", "who are you", "what can you do", "hi!", "yo", "hello there"
    ]
    if user_message.strip().lower() in greetings:
        return {
            "response": (
                "🟢 <span style='color:green'>Hey! I'm <strong>Moodify</strong> 🎧 — your Groq-powered music buddy. "
                "Tell me how you feel, your favorite artist, or the kind of music you want.</span>"
            )
        }

    # Extract intent from free-text
    extracted = extract_preferences_from_message(user_message, GROQ_API_KEY)

    # If extraction fails or all values are null
    if not extracted or not any(extracted.values()):
        clarification_prompt = f"""
The user said: "{user_message}"
They want music, but didn’t provide a genre, mood, tempo, or artist.
Ask them — nicely and in a casual way — what kind of music or vibe they’re into.
"""
        gpt_message = generate_chat_response(
            {"song": "N/A", "artist": "N/A", "genre": "N/A", "tempo": "N/A"},
            {"genre": None, "mood": None, "tempo": None},
            GROQ_API_KEY,
            custom_prompt=clarification_prompt
        )
        return {"response": f"🟢 <span style='color:green'>{gpt_message}</span>"}

    # Update session memory
    session = memory.get_session(preference.session_id)
    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        val = extracted.get(key)
        if val:
            memory.update_session(preference.session_id, key, val)

    prefs = memory.get_session(preference.session_id)
    song = recommend_engine(prefs)

    # No match fallback
    if not song or song['song'] == "N/A":
        return {
            "response": "🟢 <span style='color:green'>I couldn’t find a match. Want to try a different mood, artist, or genre?</span>"
        }

    gpt_message = generate_chat_response(song, prefs, GROQ_API_KEY)

    return {
        "response": f"🟢 <span style='color:green'>{gpt_message}</span>"
    }

@app.post("/command")
def handle_command(command_input: CommandInput):
    cmd = command_input.command.lower()
    session_id = command_input.session_id

    if "another" in cmd:
        prefs = memory.get_session(session_id)
        song = recommend_engine(prefs)
        gpt_message = generate_chat_response(song, prefs, GROQ_API_KEY)
        return {"response": f"🟢 <span style='color:green'>{gpt_message}</span>"}

    elif "change" in cmd:
        for key in ["genre", "mood", "tempo"]:
            if key in cmd:
                memory.update_session(session_id, key, None)
                return {"response": f"🟢 <span style='color:green'>What {key} would you like now?</span>"}

    return {"response": "🟢 <span style='color:green'>Try something like 'another one' or 'change vibe'.</span>"}

@app.get("/session/{session_id}")
def get_session(session_id: str):
    return memory.get_session(session_id)

@app.get("/test-cors")
def test_cors():
    return {"message": "CORS is working!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")), reload=True)
