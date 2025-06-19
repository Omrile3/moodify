"""
Contains all user-facing messages used in the application.
Messages are organized into logical categories for better maintenance and reusability.
"""

class Messages:
    """Container for all application messages organized by their context."""
    
    class Greeting:
        """Initial user interaction messages."""
        WELCOME = "Hi! I'm here to help you find music that matches your mood. How are you feeling right now? Or what kind of music would you like to hear?"

    class Recommendations:
        """Messages related to song recommendations."""
        NO_SONG_FOUND = "I couldn't find a song with a Spotify link. Want to change your preferences?"
        FEEDBACK_BUTTONS = """Are you happy with this recommendation?"""  # Used with BUTTONS_HTML
        POSITIVE_FEEDBACK = "Great! Glad you liked it. If you want to hear something else, just type 'reset' to start again any time!"

    class Preferences:
        """Messages related to user preferences and changes."""
        CHANGE_OPTIONS = "Which preference would you like to change? (genre, mood, tempo, or artist)"
        CHANGE_FIELD = "Sure! What {field} would you like instead?"  # field is replaced with actual preference
        INVALID_LAST_SONG = "I couldn't find your last song. Let's start fresh - what kind of music do you want to hear?"
        AVAILABLE_COMMANDS = "You can say 'another one', 'change genre', 'change artist', 'change mood', 'change tempo', or 'reset' to start over."

    class Reset:
        """Messages related to resetting/restarting the session."""
        CONFIRM = "🔄 Preferences reset! Tell me how you're feeling or what type of music you want to hear."
        START_FRESH = "🔁 Alright! Let's start fresh. How are you feeling right now?"

    class Error:
        """Error messages."""
        GENERIC = "An unexpected error occurred. Please try again later."

    @staticmethod
    def wrap_green(message: str) -> str:
        """Wraps a message in a green-colored span tag."""
        return f"<span style='color:green'>{message}</span>"

    @staticmethod
    def with_emoji(message: str, emoji: str) -> str:
        """Prepends an emoji to a message."""
        return f"{emoji} {message}"
