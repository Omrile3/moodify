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

    # GUARD: If awaiting feedback, do not recommend again until /command clears it!
    if session.get("awaiting_feedback", False):
        return {"response": None}

    # Always extract new info
    extracted = extract_preferences_from_message(user_message, GROQ_API_KEY)
    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        if extracted.get(key) is None and user_message.strip().lower() in ["no", "none", "no preference", "nothing", "any", "whatever", "anything", "doesn't matter", "no specific preference"]:
            memory.update_session(preference.session_id, f"no_pref_{key}", True)
        elif extracted.get(key):
            memory.update_session(preference.session_id, key, extracted[key])
            memory.update_session(preference.session_id, f"no_pref_{key}", False)

    session = memory.get_session(preference.session_id)
    all_fields = ["genre", "mood", "tempo", "artist_or_song"]
    fields_completed = [
        k for k in all_fields if session.get(k) is not None or session.get(f"no_pref_{k}", False)
    ]

    # Only recommend if ALL 4 are set or "no_pref"
    if len(fields_completed) == 4:
        song = recommend_engine(session)
        if not song or song['song'] == "N/A":
            return {
                "response": "<span style='color:green'>I couldn’t find a match. Want to try a different mood, artist, or genre?</span>"
            }
        memory.update_last_song(preference.session_id, song['song'], song['artist'])
        gpt_message = generate_chat_response(song, session, GROQ_API_KEY)
        memory.update_session(preference.session_id, "awaiting_feedback", True)
        memory.update_session(preference.session_id, "followup_count", 0)
        return {"response": f"<span style='color:green'>{gpt_message}</span><br>Was that a good fit for you?"}
    else:
        followup_count = session.get("followup_count", 0)
        if followup_count >= 4:
            # Recommend with whatever info is present, fallback logic
            fake_session = {k: session.get(k) for k in all_fields}
            for k in all_fields:
                if not fake_session[k]:
                    fake_session[k] = "any"
            song = recommend_engine(fake_session)
            if not song or song['song'] == "N/A":
                return {
                    "response": "<span style='color:green'>I couldn’t find a match. Want to try a different mood, artist, or genre?</span>"
                }
            memory.update_last_song(preference.session_id, song['song'], song['artist'])
            gpt_message = generate_chat_response(song, fake_session, GROQ_API_KEY)
            memory.update_session(preference.session_id, "followup_count", 0)
            memory.update_session(preference.session_id, "awaiting_feedback", True)
            return {"response": f"<span style='color:green'>{gpt_message}</span><br>Was that a good fit for you? Say no for another rec, or yes to keep it."}
        ai_message = next_ai_message(session, user_message, GROQ_API_KEY)
        memory.update_session(preference.session_id, "followup_count", followup_count + 1)
        return {"response": f"<span style='color:green'>{ai_message}</span>"}

@app.post("/command")
def handle_command(command_input: CommandInput):
    cmd = command_input.command.lower()
    session_id = command_input.session_id
    session = memory.get_session(session_id)

    # --- 1. PRIORITY: Change preferences if asked ---
    for pref in ["genre", "mood", "tempo", "artist"]:
        if f"change {pref}" in cmd or f"switch {pref}" in cmd or f"new {pref}" in cmd or (pref in cmd and "change" in cmd):
            # Clear the current preference and ask for new value
            field = "artist_or_song" if pref == "artist" else pref
            memory.update_session(session_id, field, None)
            memory.update_session(session_id, f"no_pref_{field}", False)  # allow user to re-specify
            memory.update_session(session_id, "awaiting_feedback", False)
            return {
                "response": f"<span style='color:green'>Sure! What {pref} would you like instead?</span>"
            }

    # --- 2. Reset session if asked ---
    if any(word in cmd for word in ["start over", "restart", "reset"]):
        memory.reset_session(session_id)
        session = memory.get_session(session_id)
        return {
            "response": (
                "🔁 <span style='color:green'>Alright! Let’s start fresh. How are you feeling right now?</span>"
            )
        }

    # --- 3. Recommend another song if user asks ---
    if any(word in cmd for word in ["another", "again", "next one"]):
        session["history"] = [(session.get("last_song"), session.get("last_artist"))]
        song = recommend_engine(session)
        if not song or song['song'] == "N/A":
            return {"response": "<span style='color:green'>I couldn’t find another one. Want to change mood, genre, artist, or tempo?</span>"}
        memory.update_last_song(session_id, song['song'], song['artist'])
        gpt_message = generate_chat_response(song, session, GROQ_API_KEY)
        memory.update_session(session_id, "awaiting_feedback", True)
        return {"response": f"<span style='color:green'>{gpt_message}</span><br>Was that a good fit for you?"}

    # --- 4. Handle feedback after recommendation ---
    if session.get("awaiting_feedback"):
        # If "no", keep recommending
        if any(word in cmd for word in ["no", "didn't", "not really", "did not", "nah", "not a good fit", "not fit", "try again"]):
            session["history"].append((session.get("last_song"), session.get("last_artist")))
            song = recommend_engine(session)
            if not song or song['song'] == "N/A":
                return {
                    "response": "<span style='color:green'>I couldn’t find another one. Want to change mood, genre, artist, or tempo?</span>"
                }
            memory.update_last_song(session_id, song['song'], song['artist'])
            gpt_message = generate_chat_response(song, session, GROQ_API_KEY)
            memory.update_session(session_id, "awaiting_feedback", True)
            return {"response": f"<span style='color:green'>{gpt_message}</span><br>Was that a good fit for you?"}
        # If "yes", close feedback loop
        if any(word in cmd for word in ["yes", "love", "liked", "good", "great", "perfect", "awesome", "sure"]):
            memory.update_session(session_id, "awaiting_feedback", False)
            return {
                "response": (
                    "😊 <span style='color:green'>Great! If you want to hear something different, just reset the chat.</span>"
                )
            }

    # --- 5. If user says what they want changed, but is vague, ask for clarification ---
    if "change" in cmd or "something else" in cmd or "different" in cmd:
        return {
            "response": (
                "<span style='color:green'>Which preference would you like to change? (genre, mood, tempo, or artist)</span>"
            )
        }

    # --- 6. Generic help ---
    return {"response": "<span style='color:green'>You can say 'another one', 'change genre', 'change artist', 'change mood', 'change tempo', or 'reset' to start over.</span>"}

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
