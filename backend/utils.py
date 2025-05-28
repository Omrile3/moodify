import base64
import os

def get_spotify_token():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Missing Spotify credentials")
        return None

    auth_str = f"{client_id}:{client_secret}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    try:
        response = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
        return response.json().get("access_token")
    except Exception as e:
        print("Spotify Token Error:", e)
        return None

def search_spotify_url(song: str, artist: str) -> str:
    token = get_spotify_token()
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    query = f"{song} {artist}"
    try:
        response = requests.get(
            "https://api.spotify.com/v1/search",
            headers=headers,
            params={"q": query, "type": "track", "limit": 1}
        )
        items = response.json().get("tracks", {}).get("items", [])
        if items:
            return items[0]["external_urls"]["spotify"]
    except Exception as e:
        print("Spotify Search Error:", e)
    return None
