class SessionMemory:
    def __init__(self):
        self.sessions = {}

    def get_session(self, session_id: str) -> dict:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "genre": None,
                "mood": None,
                "tempo": None,
                "artist_or_song": None,
                "last_song": None,
                "last_artist": None
            }
        return self.sessions[session_id]

    def update_session(self, session_id: str, key: str, value):
        if session_id not in self.sessions:
            self.get_session(session_id)
        self.sessions[session_id][key] = value

    def update_last_song(self, session_id: str, song: str, artist: str):
        if session_id not in self.sessions:
            self.get_session(session_id)
        self.sessions[session_id]["last_song"] = song
        self.sessions[session_id]["last_artist"] = artist

    def reset_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id] = {
                "genre": None,
                "mood": None,
                "tempo": None,
                "artist_or_song": None,
                "last_song": None,
                "last_artist": None
            }
