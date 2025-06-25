from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from typing import Optional
import logging

from recommender_eng import recommend_engine
from logging_config import setup_logging
from log_utils import log_dict_info, log_dict_warning, log_dict_error
from memory import SessionMemory
from preferences import (
    extract_user_preferences,
    update_session_preferences,
    has_all_preferences,
    get_missing_preferences
)
from utils import (
    generate_chat_response,
    next_ai_message
)
from constants import (
    PREFERENCE_FIELDS,
)
from messages import Messages

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

# Set up logging configuration
setup_logging()
logger = logging.getLogger(__name__)

class PreferenceInput(BaseModel):
    session_id: str
    message: Optional[str] = None
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
    
    log_dict_info("Starting recommendation search",
        session_id=session.get("session_id"),
        preferences={
            "genre": session.get("genre"),
            "mood": session.get("mood"),
            "tempo": session.get("tempo"),
            "artist_or_song": session.get("artist_or_song")
        })
    
    while attempts < max_attempts:
        song = recommend_engine(session, api_key=OPENAI_API_KEY)
        if not song or song.get('song') == "N/A":
            log_dict_warning("Invalid song returned",
                attempt=attempts + 1,
                session_id=session.get("session_id"),
                song_status="invalid")
            return None
            
        spotify_url = song.get("spotify_url")
        if spotify_url and "open.spotify.com/track/" in spotify_url:
            log_dict_info("Found valid song",
                attempt=attempts + 1,
                session_id=session.get("session_id"),
                song=song.get("song"),
                artist=song.get("artist"),
                spotify_url=song.get("spotify_url"))
            return song
            
        logger.debug(f"Song without Spotify URL on attempt {attempts + 1}")
        session.setdefault("history", []).append((song.get('song'), song.get('artist')))
        attempts += 1
        
    logger.warning("Failed to find valid song after max attempts")
    return None

def handle_song_recommendation(session_id: str, song: dict) -> dict:
    log_dict_info("Handling song recommendation",
        session_id=session_id,
        song_data=song,
        recommendation_type="spotify" if song and song.get("spotify_url") else "fallback")
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
            "response": Messages.wrap_green(Messages.Recommendations.NO_SONG_FOUND)
        }
    
    # Update session with new song
    logger.info(f"Recommending song: {song.get('song')} by {song.get('artist')}")
    memory.update_last_song(session_id, song['song'], song['artist'])
    gpt_message = generate_chat_response(song, memory.get_session(session_id), OPENAI_API_KEY)
    memory.update_session(session_id, "awaiting_feedback", True)
    
    return {
        "response": f"{Messages.wrap_green(gpt_message)}<br>{Messages.Recommendations.FEEDBACK_BUTTONS}"
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
    
    return {
        "response": Messages.wrap_green(Messages.Preferences.CHANGE_FIELD.format(field=field))
    }

def handle_user_message(session_id: str, message: str) -> dict:
    log_dict_info("Processing user message",
        session_id=session_id,
        message_length=len(message),
        message_type="preference_input")
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
        logger.info(f"All preferences set for session {session_id}, generating recommendation")
        song = get_valid_recommendation(session)
        memory.update_session(session_id, "followup_count", 0)
        return handle_song_recommendation(session_id, song)
    
    # Otherwise, continue the conversation
    ai_message = next_ai_message(session, message, OPENAI_API_KEY)
    memory.update_session(session_id, "followup_count", session.get("followup_count", 0) + 1)
    
    return {"response": Messages.wrap_green(ai_message)}

# API Routes
@app.post("/recommend")
def recommend(preference: PreferenceInput):
    """Handle user's preference input and provide recommendations."""
    log_dict_info("Received recommendation request",
        session_id=preference.session_id,
        input_preferences={
            "genre": preference.genre,
            "mood": preference.mood,
            "tempo": preference.tempo,
            "artist_or_song": preference.artist_or_song
        },
        endpoint="/recommend")
    session = memory.get_session(preference.session_id)
    user_message = preference.message.strip() if preference.message else None

    # Only show initial greeting if no message and no preferences
    if not user_message and not any([session.get(field) for field in PREFERENCE_FIELDS]) and not session.get("greeted"):
        memory.update_session(preference.session_id, "greeted", True)
        log_dict_info("New session, asking for initial preferences", session_id=preference.session_id)
        return {
            "response": Messages.wrap_green(Messages.Greeting.WELCOME)
        }

    # Block multiple recommends if waiting for feedback
    if session.get("awaiting_feedback", False):
        return {"response": None}
    
    return handle_user_message(preference.session_id, user_message)

@app.post("/command")
def handle_command(command_input: CommandInput):
    """Handle user commands and feedback.
    possible commands:
    LOVE_SONG_COMMAND = "yes".lower()
    RECOMMAND_ANOTHER_COMMAND = "no".lower()
    CHANGE_MOOD_COMMAND = "change mood".lower()
    CHANGE_GENRE_COMMAND = "change genre".lower()
    CHANGE_ARTIST_COMMAND = "change artist".lower()
    CHANGE_TEMPO_COMMAND = "change tempo".lower()  
    """
    cmd = command_input.command.lower()
    session_id = command_input.session_id
    session = memory.get_session(session_id)
    
    log_dict_info("Processing command",
        session_id=session_id,
        command=cmd,
        awaiting_feedback=session.get("awaiting_feedback", False),
        current_preferences={
            "genre": session.get("genre"),
            "mood": session.get("mood"),
            "tempo": session.get("tempo"),
            "artist_or_song": session.get("artist_or_song")
        })
    CHANGE_COMMANDS = [Messages.Recommendations.CHANGE_MOOD_COMMAND, Messages.Recommendations.CHANGE_GENRE_COMMAND, Messages.Recommendations.CHANGE_ARTIST_COMMAND, Messages.Recommendations.CHANGE_TEMPO_COMMAND]
    # Preference change commands
    if cmd in CHANGE_COMMANDS:
        logger.info(f"Handling preference change command: {cmd} for session {session_id}")
        pref = cmd.split("change ")[-1]  # Extract preference from command        
        logger.info(f"Changing preference {pref} for session {session_id}")
        return handle_preference_change(session_id, pref)
                

    elif cmd == Messages.Recommendations.RECOMMAND_ANOTHER_COMMAND or cmd == Messages.Recommendations.LOVE_SONG_COMMAND:
        logger.info(f"Handling recommendation command: {cmd} for session {session_id}")
        #Generate a new recommendation
        song = get_valid_recommendation(session)
        memory.update_session(session_id, "followup_count", 0)
        return handle_song_recommendation(session_id, song)

    else:
        logger.info(f"Received unrecognized command: {cmd} for session {session_id}")
        # Handle unrecognized commands
        return {
            "response": Messages.wrap_green(Messages.Error.INVALID_COMMAND)
        }
        
    # if any(word in cmd for word in ["start over", "restart", "reset"]):
    #     logger.info(f"Resetting session {session_id}")
    #     memory.reset_session(session_id)
    #     return {
    #         "response": Messages.with_emoji(Messages.wrap_green(Messages.Reset.START_FRESH), "🔁")
    #     }

    # if any(word in cmd for word in ["another", "again", "next one"]):
    #     session["history"] = [(session.get("last_song"), session.get("last_artist"))]
    #     song = get_valid_recommendation(session)
    #     return handle_song_recommendation(session_id, song)

    # # Handle feedback after recommendation
    # if session.get("awaiting_feedback"):
    #     last_song = session.get("last_song")
    #     last_artist = session.get("last_artist")
        
    #     # Verify we have a valid last song before handling feedback
    #     if not last_song or not last_artist:
    #         memory.update_session(session_id, "awaiting_feedback", False)
    #         return {
    #             "response": Messages.wrap_green(Messages.Preferences.INVALID_LAST_SONG)
    #         }
        
    #     if any(word in cmd for word in NEGATIVE_FEEDBACK):
    #         logger.info(f"Negative feedback received for song: {last_song} by {last_artist}")
    #         # Add last song to history if not already there
    #         if (last_song, last_artist) not in session["history"]:
    #             session["history"].append((last_song, last_artist))
            
    #         # Get new recommendation
    #         song = get_valid_recommendation(session)
    #         return handle_song_recommendation(session_id, song)
            
    #     if any(word in cmd for word in POSITIVE_FEEDBACK):
    #         logger.info(f"Positive feedback received for song: {last_song} by {last_artist}")
    #         memory.update_session(session_id, "awaiting_feedback", False)
    #         return {
    #             "response": Messages.with_emoji(Messages.wrap_green(Messages.Recommendations.POSITIVE_FEEDBACK), "😊")
    #         }
    #     # Check for new preferences in feedback
    #     logger.info(f"Checking for new preferences in feedback: {cmd}")
    #     extracted = extract_user_preferences(cmd, OPENAI_API_KEY)
    #     if any(extracted.get(k) for k in PREFERENCE_FIELDS):
    #         for key in PREFERENCE_FIELDS:
    #             if extracted.get(key):
    #                 memory.update_session(session_id, key, extracted[key])
    #         song = get_valid_recommendation(session)
    #         return handle_song_recommendation(session_id, song)
    #     return {"response": Messages.wrap_green(Messages.Preferences.AVAILABLE_COMMANDS)}

    # if "change" in cmd or "something else" in cmd or "different" in cmd:
    #     return {
    #         "response": Messages.wrap_green(Messages.Preferences.CHANGE_OPTIONS)
    #     }
    # return {"response": Messages.wrap_green(Messages.Preferences.AVAILABLE_COMMANDS)}

@app.post("/reset")
def reset_session(command_input: CommandInput):
    session_id = command_input.session_id
    memory.reset_session(session_id)
    memory.update_session(session_id, "greeted", False)  # Reset greeting flag
    return {
        "response": Messages.with_emoji(Messages.wrap_green(Messages.Reset.CONFIRM), "🔄")
    }

@app.get("/session/{session_id}")
def get_session(session_id: str):
    return memory.get_session(session_id)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    error_details = traceback.format_exc()
    log_dict_error("Unhandled exception occurred",
        error=str(exc),
        traceback=error_details)
    return JSONResponse(
        status_code=500,
        content={"message": Messages.Error.GENERIC},
    )

@app.get("/test-cors")
def test_cors():
    return {"message": "CORS is working!"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Moodify backend server...")
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")), reload=True)
