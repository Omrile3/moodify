class SessionMemory:
    def __init__(self):
        self.sessions = {}

    def get_session(self, session_id: str) -> dict:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "genre": None,
                "mood": None,
                "tempo": None,
                "artist_or_song": None
            }
        return self.sessions[session_id]

    def update_session(self, session_id: str, key: str, value):
        if session_id not in self.sessions:
            self.get_session(session_id)
        self.sessions[session_id][key] = value

    def reset_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id] = {
                "genre": None,
                "mood": None,
                "tempo": None,
                "artist_or_song": None
            }
