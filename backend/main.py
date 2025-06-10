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

def is_music_related(text: str) -> bool:
    keywords = ["music", "song", "artist", "genre", "playlist", "recommend", "mood", "tempo"]
    return any(word in text.lower() for word in keywords)

def detect_keys_to_change(message: str):
    keys = []
    message = message.lower()
    if "genre" in message:
        keys.append("genre")
    if "mood" in message:
        keys.append("mood")
    if "tempo" in message:
        keys.append("tempo")
    if "artist" in message:
        keys.append("artist_or_song")
    return keys

# After extracting/receiving tempo, normalize common typos
def normalize_tempo(tempo):
    if not tempo:
        return tempo
    t = tempo.strip().lower().replace(",", "")
    if t in ["mediu", "medum", "med", "mid"]:
        return "medium"
    if t in ["slw", "slwo", "slo"]:
        return "slow"
    if t in ["fas", "fst", "faast"]:
        return "fast"
    return tempo

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

    greetings = ["hello", "hi", "start", "hey", "who are you", "what can you do", "hi!", "yo", "hello there"]
    if user_message.strip().lower() in greetings:
        return {
            "response": (
                "<span style='color:green'>Hey! I’m <strong>Moodify</strong> 🎧 — your AI-powered music buddy.<br>"
                "Let’s find your perfect song! Tell me how you’re feeling or what kind of vibe you’re into.</span>"
            )
        }

    # Handle follow-up questions if pending
    if "pending_questions" in session and session["pending_questions"]:
        current = session["pending_questions"].pop(0)
        normalized = user_message.strip().lower()
        none_like = [
            "no", "none", "nah", "not really", "nothing",
            "any", "anything", "whatever", "doesn't matter", "does not matter", "no preference", "up to you",
            "anything is fine", "i don't care", "i don't mind", "doesn't matter to me", "no specific preference", "no prefernce"
        ]
        value = None if any(phrase in normalized for phrase in none_like) else user_message
        extracted = extract_preferences_from_message(user_message, GROQ_API_KEY)
        logging.info(f"[Extraction][PendingQ] User message: '{user_message}' | Extracted: {extracted}")

        # Robust handling for artist_or_song: treat any "none-like" answer as None
        if current == "artist_or_song":
            if any(phrase in normalized for phrase in none_like):
                value = None
                extracted["artist_or_song"] = None
            elif extracted.get("artist_or_song") and any(phrase in extracted["artist_or_song"].lower() for phrase in none_like):
                value = None
                extracted["artist_or_song"] = None

        memory.update_session(preference.session_id, current, value)
        for key in ["genre", "mood", "tempo", "artist_or_song"]:
            if extracted.get(key):
                memory.update_session(preference.session_id, key, extracted[key])

        session = memory.get_session(preference.session_id)
        if session["pending_questions"]:
            next_q = session["pending_questions"][0]
            return {"response": question_for_key(next_q)}
        else:
            # Resume with updated prefs
            return recommend(PreferenceInput(session_id=preference.session_id))

    # Always try to extract preferences from the message
    extracted = extract_preferences_from_message(user_message, GROQ_API_KEY)
    logging.info(f"[Extraction][Main] User message: '{user_message}' | Extracted: {extracted}")
    for key in ["genre", "mood", "tempo", "artist_or_song"]:
        if extracted.get(key):
            memory.update_session(preference.session_id, key, extracted[key])

    session = memory.get_session(preference.session_id)

    # Check for missing preferences
    # Only ask for missing if the value is not present AND not explicitly set to None by the user
    required_keys = ["genre", "mood", "tempo", "artist_or_song"]
    missing = [key for key in required_keys if key not in session or session[key] is None]
    if missing:
        session["pending_questions"] = missing
        memory.update_session(preference.session_id, "pending_questions", missing)
        return {"response": question_for_key(missing[0])}
    else:
        # recommend
        song = recommend_engine(session)
        if not song or song['song'] == "N/A":
            return {
                "response": "<span style='color:green'>I couldn’t find a match. Want to try a different mood, artist, or genre?</span>"
            }

        memory.update_last_song(preference.session_id, song['song'], song['artist'])
        gpt_message = generate_chat_response(song, session, GROQ_API_KEY)
        # Set awaiting_feedback flag
        memory.update_session(preference.session_id, "awaiting_feedback", True)

        return {"response": f"<span style='color:green'>{gpt_message}</span><br>Was that a good fit for you?"}

def question_for_key(key: str) -> str:
    prompts = {
        "genre": "<span style='color:green'>What genre do you usually enjoy?</span>",
        "mood": "<span style='color:green'>How are you feeling right now? (e.g., happy, sad, calm)</span>",
        "tempo": "<span style='color:green'>Would you prefer a slow, medium, or fast-paced song?</span>",
        "artist_or_song": "<span style='color:green'>Do you have a favorite artist?</span>"
    }
    return prompts.get(key, "Could you clarify that?")

@app.post("/command")
def handle_command(command_input: CommandInput):
    cmd = command_input.command.lower()
    session_id = command_input.session_id
    session = memory.get_session(session_id)

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
            # Build a summary of user preferences for the message
            prefs = []
            if session.get("genre"):
                prefs.append(session["genre"])
            if session.get("mood"):
                prefs.append(session["mood"])
            if session.get("tempo"):
                prefs.append(session["tempo"])
            if session.get("artist_or_song"):
                prefs.append(session["artist_or_song"])
            prefs_str = ", ".join(str(p) for p in prefs if p)
            # Reset the flag
            memory.update_session(session_id, "awaiting_feedback", False)
            return {
                "response": (
                    f"😔 <span style='color:green'>I'm sorry that the song isn't quite right for you."
                    f" I looked up a <b>{prefs_str}</b> song for you."
                    " Would you like another one? Alternatively, you can say 'change genre', 'change mood', 'change artist', or 'reset' to update your preferences.</span>"
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
                "If you want to discover more, you can say things like 'another one', 'change genre', or 'change artist'.<br>"
                "You can also reset your preferences anytime by saying 'reset'.</span>"
            )
        }

    # Interpret direct reply to change
    keys = detect_keys_to_change(cmd)
    if keys:
        session["pending_questions"] = keys
        memory.update_session(session_id, "pending_questions", keys)
        return {"response": question_for_key(keys[0])}

    return {"response": "<span style='color:green'>You can say 'another one', 'change genre', 'change artist', or 'reset' to start over.</span>"}

@app.post("/reset")
def reset_session(command_input: CommandInput):
    session_id = command_input.session_id
    memory.reset_session(session_id)
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
