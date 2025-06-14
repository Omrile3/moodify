from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from typing import Optional
import logging

from recommender_eng import recommend_engine
from memory import SessionMemory
from utils import generate_chat_response, extract_preferences_from_message, GENRES, next_ai_message

# Load Groq key
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI()
memory = SessionMemory()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://moodify-frontend-cheh.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

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
    user_message = (
        preference.artist_or_song
        or preference.genre
        or preference.mood
        or preference.tempo
        or ""
    )
    session = memory.get_session(preference.session_id)

    # Always extract new info
    extracted = extract_preferences_from_message(user_message, GROQ_API_KEY)
    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        if extracted.get(key):
            memory.update_session(preference.session_id, key, extracted[key])
    session = memory.get_session(preference.session_id)

    required_keys = ["genre", "mood", "tempo", "artist_or_song"]
    # If all info present, recommend song
    if all(session.get(k) for k in required_keys):
        song = recommend_engine(session)
        if not song or song['song'] == "N/A":
            return {
                "response": "<span style='color:green'>I couldn’t find a match. Want to try a different mood, artist, or genre?</span>"
            }
        memory.update_last_song(preference.session_id, song['song'], song['artist'])
        gpt_message = generate_chat_response(song, session, GROQ_API_KEY)
        memory.update_session(preference.session_id, "awaiting_feedback", True)
        return {"response": f"<span style='color:green'>{gpt_message}</span><br>Was that a good fit for you?"}
    else:
        # Let AI decide what to ask next
        ai_message = next_ai_message(session, user_message, GROQ_API_KEY)
        return {"response": f"<span style='color:green'>{ai_message}</span>"}

@app.post("/command")
def handle_command(command_input: CommandInput):
    cmd = command_input.command.lower()
    session_id = command_input.session_id
    session = memory.get_session(session_id)

    # Reset session if asked
    if "start over" in cmd or "restart" in cmd or "reset" in cmd:
        memory.reset_session(session_id)
        session = memory.get_session(session_id)
        return {
            "response": (
                "🔁 <span style='color:green'>Alright! Let’s start fresh. How are you feeling right now?</span>"
            )
        }
    # Give another suggestion if requested
    if "another" in cmd or "again" in cmd:
        session["history"] = [(session.get("last_song"), session.get("last_artist"))]
        song = recommend_engine(session)
        if not song or song['song'] == "N/A":
            return {"response": "<span style='color:green'>I couldn’t find another one. Want to change mood or artist?</span>"}
        memory.update_last_song(session_id, song['song'], song['artist'])
        gpt_message = generate_chat_response(song, session, GROQ_API_KEY)
        return {"response": f"<span style='color:green'>{gpt_message}</span><br>Did you like that one?"}

    elif "change" in cmd or "didn't like" in cmd or "no" in cmd:
        if session.get("awaiting_feedback"):
            prefs = [session.get(k) for k in ["genre", "mood", "tempo", "artist_or_song"] if session.get(k)]
            prefs_str = ", ".join(prefs)
            memory.update_session(session_id, "awaiting_feedback", False)
            return {
                "response": (
                    f"😔 <span style='color:green'>I'm sorry that wasn't quite right. "
                    f"I looked up a <b>{prefs_str}</b> song. Want another one?</span>"
                )
            }
        else:
            return {
                "response": (
                    "🔁 <span style='color:green'>What would you like to change in your preferences? "
                    "(genre, mood, tempo, artist)</span>"
                )
            }

    elif "yes" in cmd or "love" in cmd or "liked" in cmd or "good" in cmd:
        memory.update_session(session_id, "awaiting_feedback", False)
        return {
            "response": (
                "😊 <span style='color:green'>I'm glad you liked it! "
                "Say 'another one', 'change genre', or 'reset' anytime to explore more.</span>"
            )
        }

    return {"response": "<span style='color:green'>You can say 'another one', 'change genre', 'change artist', or 'reset' to start over.</span>"}

@app.post("/reset")
def reset_session(command_input: CommandInput):
    session_id = command_input.session_id
    memory.reset_session(session_id)
    session = memory.get_session(session_id)
    return {
        "response": (
            "🔄 <span style='color:green'>Preferences reset! Tell me how you’re feeling or what type of music you want to hear.</span>"
        )
    }

@app.get("/session/{session_id}")
def get_session(session_id: str):
    return memory.get_session(session_id)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    error_details = traceback.format_exc()
    print(f"Unhandled exception: {exc}\nDetails:\n{error_details}")
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred. Please try again later."},
    )

@app.get("/test-cors")
def test_cors():
    return {"message": "CORS is working!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")), reload=True)
