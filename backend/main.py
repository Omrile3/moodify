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

    # Extract preferences using Groq
    extracted = extract_preferences_from_message(user_message, GROQ_API_KEY)

    if not extracted or not any(extracted.values()):
        clarification_prompt = f"""
        The user said: "{user_message}"
        But didn’t provide enough details. Ask — in a casual way — what genre, artist, or vibe they want.
        """
        clarification = generate_chat_response(
            {"song": "N/A", "artist": "N/A", "genre": "N/A", "tempo": "N/A"},
            {"genre": None, "mood": None, "tempo": None},
            GROQ_API_KEY,
            custom_prompt=clarification_prompt
        )
        return {"response": f"🟢 <span style='color:green'>{clarification}</span>"}

    # Update session state with extracted values
    session = memory.get_session(preference.session_id)
    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        val = extracted.get(key)
        if val:
            memory.update_session(preference.session_id, key, val)

    # Merge direct user inputs too
    prefs = memory.get_session(preference.session_id)
    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        if preference.dict().get(key):
            prefs[key] = preference.dict()[key]

    # Run recommender engine
    song = recommend_engine(prefs, prefs.get("history"))

    # Ask more if still not enough data
    if not song or song['song'] == "N/A":
        clarification_prompt = f"""
        The user said: "{user_message}".
        Still missing enough info. Ask politely what genre, artist, or mood they like to help refine the match.
        """
        clarification = generate_chat_response(
            {"song": "N/A", "artist": "N/A", "genre": "N/A", "tempo": "N/A"},
            prefs,
            GROQ_API_KEY,
            custom_prompt=clarification_prompt
        )
        return {"response": f"🟢 <span style='color:green'>{clarification}</span>"}

    # Track song in session history
    memory.add_to_history(preference.session_id, song["song"])
    gpt_message = generate_chat_response(song, prefs, GROQ_API_KEY)

    # Construct HTML response
    note = f"{song['note']}<br>" if song.get("note") else ""
    response_html = f"🟢 <span style='color:green'>{note}{gpt_message}</span>"

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
