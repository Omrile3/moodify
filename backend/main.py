from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv
from typing import Optional

from recommender_eng import recommend_engine
from memory import SessionMemory
from utils import (
    generate_chat_response,
    extract_preferences_from_message,
    search_spotify_preview
)

# Load environment variables
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

    greetings = ["hello", "hi", "start", "hey", "who are you", "what can you do"]
    if user_message.strip().lower() in greetings:
        return {
            "response": (
                "<span style='color:green'>Hey! I'm <strong>Moodify</strong> 🎧 — your AI-powered music buddy.<br>"
                "To get started, tell me one or more of the following:<br>"
                "• 🎵 Your favorite artist or band<br>"
                "• 🎧 The kind of music or genre you like<br>"
                "• 😊 How you're feeling or your current mood<br>"
                "Let’s find your perfect song!</span>"
            )
        }

    # 1. Extract preferences using Groq
    extracted = extract_preferences_from_message(user_message, GROQ_API_KEY)

    # 2. Store and update session memory
    session = memory.get_session(preference.session_id)
    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        user_val = preference.dict().get(key)
        extracted_val = extracted.get(key)
        if user_val:
            memory.update_session(preference.session_id, key, user_val)
        elif extracted_val:
            memory.update_session(preference.session_id, key, extracted_val)

    prefs = memory.get_session(preference.session_id)

    # 3. If not enough data, ask guiding question
    if not prefs.get("artist_or_song") and not prefs.get("genre") and not prefs.get("mood"):
        prompt = f"The user said: \"{user_message}\" but didn’t give a clear artist, mood, or genre. Ask what kind of vibe or music they want."
        guidance = generate_chat_response(
            {"song": "N/A", "artist": "N/A", "genre": "N/A", "tempo": "N/A"},
            prefs,
            GROQ_API_KEY,
            custom_prompt=prompt
        )
        return {"response": f"🟢 <span style='color:green'>{guidance}</span>"}

    # 4. Recommend a song using preferences
    song = recommend_engine(prefs, prefs.get("history"))

    if not song or song["song"] == "N/A":
        if prefs.get("artist_or_song"):
            fallback_msg = f"🟢 <span style='color:green'>I couldn’t find a match for '{prefs['artist_or_song']}'. Can you tell me more about your favorite genre or mood?</span>"
        else:
            fallback_prompt = f"The user previously said: \"{user_message}\" but no clear match was found. Ask casually if they have a favorite artist, genre, or mood."
            fallback_msg = generate_chat_response(
                {"song": "N/A", "artist": "N/A", "genre": "N/A", "tempo": "N/A"},
                prefs,
                GROQ_API_KEY,
                custom_prompt=fallback_prompt
            )
        return {"response": fallback_msg}

    memory.add_to_history(preference.session_id, song["song"])
    gpt_msg = generate_chat_response(song, prefs, GROQ_API_KEY)

    response_html = f"🟢 <span style='color:green'>{song.get('note', '')}<br>{gpt_msg}</span>"
    if song.get("preview_url"):
        response_html += f"<br><audio controls src='{song['preview_url']}'></audio>"
    elif song.get("spotify_url"):
        response_html += f"<br><a href='{song['spotify_url']}' target='_blank'>🎧 Listen on Spotify</a>"
    else:
        response_html += "<br>⚠️ No Spotify preview available."

    return {"response": response_html}

@app.post("/command")
def handle_command(command_input: CommandInput):
    cmd = command_input.command.lower()
    session_id = command_input.session_id
    prefs = memory.get_session(session_id)

    if "another" in cmd:
        song = recommend_engine(prefs, prefs.get("history"))
        memory.add_to_history(session_id, song["song"])
        gpt_message = generate_chat_response(song, prefs, GROQ_API_KEY)
        return {"response": f"🟢 <span style='color:green'>{gpt_message}</span>"}

    elif "change" in cmd:
        for key in ["genre", "mood", "tempo"]:
            if key in cmd:
                memory.update_session(session_id, key, None)
                return {"response": f"🟢 <span style='color:green'>What {key} would you like now?</span>"}

    return {"response": "🟢 <span style='color:green'>Try saying something like 'another one' or 'change vibe'.</span>"}

@app.get("/session/{session_id}")
def get_session(session_id: str):
    return memory.get_session(session_id)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print("Error:", traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"message": "Something went wrong. Please try again."},
    )

@app.get("/test-cors")
def test_cors():
    return {"message": "CORS is working!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")), reload=True)
