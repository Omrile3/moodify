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
from utils import generate_chat_response, next_ai_message
from preferences import (
    extract_user_preferences,
    update_session_preferences,
    has_all_preferences,
    get_missing_preferences
)
from constants import (
    BUTTONS_HTML,
    POSITIVE_FEEDBACK,
    NEGATIVE_FEEDBACK,
    CHANGE_COMMANDS,
    PREFERENCE_FIELDS
)

# Load OpenAI key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


app = FastAPI()
memory = SessionMemory()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://moodify-frontend-cheh.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PreferenceInput(BaseModel):
    session_id: str
    genre: Optional[str] = None
    mood: Optional[str] = None
    tempo: Optional[str] = None
    artist_or_song: Optional[str] = None

class CommandInput(BaseModel):
    session_id: str
    command: str


def get_valid_recommendation(session):
    """Get a valid song recommendation with Spotify URL."""
    attempts = 0
    max_attempts = 10
    while attempts < max_attempts:
        song = recommend_engine(session, api_key=OPENAI_API_KEY)
        if not song or song.get('song') == "N/A":
            logger.warning(f"Invalid song returned on attempt {attempts + 1}")
            return None
            
        spotify_url = song.get("spotify_url")
        if spotify_url and "open.spotify.com/track/" in spotify_url:
            logger.info(f"Found valid song with Spotify URL on attempt {attempts + 1}")
            return song
            
        logger.debug(f"Song without Spotify URL on attempt {attempts + 1}")
        session.setdefault("history", []).append((song.get('song'), song.get('artist')))
        attempts += 1
        
    logger.warning("Failed to find valid song after max attempts")
    return None

def handle_song_recommendation(session_id: str, song: dict) -> dict:
    """
    Handle song recommendation response formatting.
    
    Args:
        session_id: Session identifier
        song: Song recommendation data
    
    Returns:
        API response dictionary
    """
    if not song:
        logger.info(f"No song found for session {session_id}")
        return {
            "response": "<span style='color:green'>I couldn't find a song with a Spotify link. Want to change your preferences?</span>"
        }
    
    # Update session with new song
    logger.info(f"Recommending song: {song.get('song')} by {song.get('artist')}")
    memory.update_last_song(session_id, song['song'], song['artist'])
    gpt_message = generate_chat_response(song, memory.get_session(session_id), OPENAI_API_KEY)
    memory.update_session(session_id, "awaiting_feedback", True)
    
    return {
        "response": f"<span style='color:green'>{gpt_message}</span><br>Are you happy with this recommendation?{BUTTONS_HTML}"
    }


def handle_preference_change(session_id: str, field: str) -> dict:
    """
    Handle preference change request.
    
    Args:
        session_id: Session identifier
        field: Preference field to change
    
    Returns:
        API response dictionary
    """
    logger.info(f"Changing preference {field} for session {session_id}")
    memory.update_session(session_id, field, None)
    memory.update_session(session_id, f"no_pref_{field}", False)
    memory.update_session(session_id, "awaiting_feedback", False)
    
    display_field = "artist" if field == "artist_or_song" else field
    return {
        "response": f"<span style='color:green'>Sure! What {display_field} would you like instead?</span>"
    }

def handle_user_message(session_id: str, message: str) -> dict:
    """
    Process user message and update preferences.
    
    Args:
        session_id: Session identifier
        message: User input message
    
    Returns:
        API response dictionary
    """
    session = memory.get_session(session_id)
    
    # Extract preferences from message
    extracted = extract_user_preferences(message, OPENAI_API_KEY)
    logger.info(f"Extracted preferences: {extracted}")
    
    # Update session with new preferences
    update_session_preferences(session, extracted)
    logger.debug(f"Updated session preferences: {session}")
    
    # If all preferences are set, return recommendation
    if has_all_preferences(session):
        song = get_valid_recommendation(session)
        memory.update_session(session_id, "followup_count", 0)
        return handle_song_recommendation(session_id, song)
    
    # Otherwise, continue the conversation
    context = build_conversation_context(session)
    ai_message = next_ai_message(session, message + "\n\n" + context, OPENAI_API_KEY)
    memory.update_session(session_id, "followup_count", session.get("followup_count", 0) + 1)
    
    return {"response": f"<span style='color:green'>{ai_message}</span>"}

def build_conversation_context(session: dict) -> str:
    """
    Build context string for conversation.
    
    Args:
        session: Current session dictionary
    
    Returns:
        Formatted context string
    """
    known_prefs = {k: session.get(k) for k in PREFERENCE_FIELDS}
    missing = get_missing_preferences(session)
    no_prefs = [k for k in PREFERENCE_FIELDS if session.get(f"no_pref_{k}", False)]
    
    return (
        f"Known preferences: {known_prefs}. "
        f"Still missing: {missing}. "
        f"User said no preference for: {no_prefs}."
    )

# API Routes
@app.post("/recommend")
def recommend(preference: PreferenceInput):
    """Handle user's preference input and provide recommendations."""
    logger.info(f"Received recommend request for session {preference.session_id}")
    # Block multiple recommends if waiting for feedback
    session = memory.get_session(preference.session_id)
    if session.get("awaiting_feedback", False):
        return {"response": None}

    # Process user message
    user_message = (
        preference.artist_or_song
        or preference.genre
        or preference.mood
        or preference.tempo
        or ""
    )
    
    return handle_user_message(preference.session_id, user_message)

@app.post("/command")
def handle_command(command_input: CommandInput):
    """Handle user commands and feedback."""
    cmd = command_input.command.lower()
    session_id = command_input.session_id
    session = memory.get_session(session_id)
    
    logger.info(f"Processing command: {cmd}")

    # Preference change commands
    for pref in ["genre", "mood", "tempo", "artist"]:
        if f"change {pref}" in cmd or f"switch {pref}" in cmd or f"new {pref}" in cmd or (pref in cmd and "change" in cmd):
            field = "artist_or_song" if pref == "artist" else pref
            return handle_preference_change(session_id, field)

    if any(word in cmd for word in ["start over", "restart", "reset"]):
        logger.info(f"Resetting session {session_id}")
        memory.reset_session(session_id)
        return {
            "response": (
                "🔁 <span style='color:green'>Alright! Let’s start fresh. How are you feeling right now?</span>"
            )
        }

    if any(word in cmd for word in ["another", "again", "next one"]):
        session["history"] = [(session.get("last_song"), session.get("last_artist"))]
        song = get_valid_recommendation(session)
        return handle_song_recommendation(session_id, song)

    # Handle feedback after recommendation
    if session.get("awaiting_feedback"):
        last_song = session.get("last_song")
        last_artist = session.get("last_artist")
        
        # Verify we have a valid last song before handling feedback
        if not last_song or not last_artist:
            memory.update_session(session_id, "awaiting_feedback", False)
            return {
                "response": "<span style='color:green'>I couldn't find your last song. Let's start fresh - what kind of music do you want to hear?</span>"
            }
        
        if any(word in cmd for word in NEGATIVE_FEEDBACK):
            logger.info(f"Negative feedback received for song: {last_song} by {last_artist}")
            # Add last song to history if not already there
            if (last_song, last_artist) not in session["history"]:
                session["history"].append((last_song, last_artist))
            
            # Get new recommendation
            song = get_valid_recommendation(session)
            return handle_song_recommendation(session_id, song)
            
        if any(word in cmd for word in POSITIVE_FEEDBACK):
            logger.info(f"Positive feedback received for song: {last_song} by {last_artist}")
            memory.update_session(session_id, "awaiting_feedback", False)
            return {
                "response": (
                    "😊 <span style='color:green'>Great! Glad you liked it. If you want to hear something else, just type 'reset' to start again any time!</span>"
                )
            }
        # Check for new preferences in feedback
        logger.info(f"Checking for new preferences in feedback: {cmd}")
        extracted = extract_user_preferences(cmd, OPENAI_API_KEY)
        if any(extracted.get(k) for k in PREFERENCE_FIELDS):
            for key in PREFERENCE_FIELDS:
                if extracted.get(key):
                    memory.update_session(session_id, key, extracted[key])
            song = get_valid_recommendation(session)
            return handle_song_recommendation(session_id, song)
        return {"response": "<span style='color:green'>You can say 'another one', 'change genre', 'change artist', 'change mood', 'change tempo', or 'reset' to start over.</span>"}

    if "change" in cmd or "something else" in cmd or "different" in cmd:
        return {
            "response": (
                "<span style='color:green'>Which preference would you like to change? (genre, mood, tempo, or artist)</span>"
            )
        }
    return {"response": "<span style='color:green'>You can say 'another one', 'change genre', 'change artist', 'change mood', 'change tempo', or 'reset' to start over.</span>"}

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
    logger.error(f"Unhandled exception: {exc}")
    logger.error(f"Details:\n{error_details}")
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred. Please try again later."},
    )

@app.get("/test-cors")
def test_cors():
    return {"message": "CORS is working!"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Moodify backend server...")
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")), reload=True)
