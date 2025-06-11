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
                "history": set()  # Track previously recommended track names
            }
        return self.sessions[session_id]

    def update_session(self, session_id: str, key: str, value):
        if session_id not in self.sessions:
            self.get_session(session_id)
        self.sessions[session_id][key] = value

    def add_to_history(self, session_id: str, track_name: str):
        if session_id in self.sessions and "history" in self.sessions[session_id]:
            self.sessions[session_id]["history"].add(track_name)

    def reset_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id] = {
                "genre": None,
                "mood": None,
                "tempo": None,
                "artisst_or_song": None,
                "history": set()
            }
