from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv
from typing import Optional

from recommender_eng import recommend_engine
from memory import SessionMemory
from utils import generate_chat_response, extract_preferences_from_message, GENRES

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

    greetings = ["hello", "hi", "start", "hey", "who are you", "what can you do", "hi!", "yo", "hello there"]
    if user_message.strip().lower() in greetings:
        return {
            "response": (
                "🟢 <span style='color:green'>Hey! I’m <strong>Moodify</strong> 🎧 — your AI-powered music buddy.<br>"
                "Here’s how you can get started:<br><ul>"
                "<li>🎵 Tell me how you’re feeling (e.g. happy, sad, chill)</li>"
                "<li>🎤 Mention your favorite artist or band</li>"
                "<li>🎧 Describe the kind of music you want to hear</li>"
                "</ul>I’ll find the perfect song for your vibe!</span>"
            )
        }

    extracted = extract_preferences_from_message(user_message, GROQ_API_KEY)
    print("🎤 Extracted:", extracted)

    if "more upbeat" in user_message.lower():
        extracted["mood"] = "happy"
        extracted["tempo"] = "fast"

    # Genre override patch
    for g in GENRES:
        if g in user_message.lower() and not extracted.get("genre"):
            extracted["genre"] = g
            print(f"🎼 Genre override detected: {g}")

    prefs = memory.get_session(preference.session_id)

    lowered_msg = user_message.lower()
    if any(phrase in lowered_msg for phrase in ["similar to", "like", "vibe like", "sounds like", "in the style of"]):
        for artist in [prefs.get("artist_or_song"), extracted.get("artist_or_song")]:
            if artist:
                extracted["artist_or_song"] = artist
                extracted["exclude_artist"] = artist
                print(f"Similarity mode — will exclude: {artist}")
                break

    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        if not extracted.get(key):
            extracted[key] = prefs.get(key)
        elif key == "artist_or_song" and extracted.get(key) != prefs.get(key):
            print(f"New artist detected: {extracted.get(key)} (was: {prefs.get(key)})")

    if not any(extracted.values()):
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

    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        if extracted.get(key):
            memory.update_session(preference.session_id, key, extracted[key])

    updated_prefs = memory.get_session(preference.session_id)
    updated_prefs["history"] = [(updated_prefs.get("last_song"), updated_prefs.get("last_artist"))]
    if extracted.get("exclude_artist"):
        updated_prefs["artist_or_song"] = extracted["artist_or_song"]
        updated_prefs["exclude_artist"] = extracted["exclude_artist"]

    song = recommend_engine(updated_prefs)

    if not song or song['song'] == "N/A":
        return {
            "response": "🟢 <span style='color:green'>I couldn’t find a match. Want to try a different mood, artist, or genre?</span>"
        }

    memory.update_last_song(preference.session_id, song['song'], song['artist'])
    gpt_message = generate_chat_response(song, updated_prefs, GROQ_API_KEY)

    if song.get("artist_not_found"):
        requested = song["requested_artist"].title()
        response = (
            f"🟠 <span style='color:orange'>I couldn’t find a song by <strong>{requested}</strong>, "
            f"but here’s something similar you might enjoy:</span><br>"
            f"<span style='color:green'>{gpt_message}</span>"
        )
    else:
        response = f"🟢 <span style='color:green'>{gpt_message}</span>"

    return {"response": response}

@app.post("/command")
def handle_command(command_input: CommandInput):
    cmd = command_input.command.lower()
    session_id = command_input.session_id

    if "another" in cmd:
        prefs = memory.get_session(session_id)
        prefs["history"] = [(prefs.get("last_song"), prefs.get("last_artist"))]
        song = recommend_engine(prefs)
        if not song or song['song'] == "N/A":
            return {"response": "🟢 <span style='color:green'>Hmm, couldn't find more. Try changing the artist, genre or mood?</span>"}
        memory.update_last_song(session_id, song['song'], song['artist'])
        gpt_message = generate_chat_response(song, prefs, GROQ_API_KEY)
        return {"response": f"🟢 <span style='color:green'>{gpt_message}</span>"}

    elif "change" in cmd:
        for key in ["genre", "mood", "tempo", "artist_or_song"]:
            if key in cmd:
                memory.update_session(session_id, key, None)
                return {"response": f"🟢 <span style='color:green'>What {key} would you like now?</span>"}

    return {"response": "🟢 <span style='color:green'>Try something like 'another one' or 'change vibe'.</span>"}

@app.post("/reset")
def reset_session(command_input: CommandInput):
    session_id = command_input.session_id
    memory.reset_session(session_id)
    return {
        "response": (
            "🟢 <span style='color:green'>Preferences reset! I'm <strong>Moodify</strong> 🎧 — "
            "tell me how you feel, your favorite artist, or the kind of music you want.</span>"
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
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")), reload=True)
