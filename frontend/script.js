const backendUrl = "https://moodify-backend-uj8d.onrender.com"; // Update this if testing locally or on a different deployment

// Improved error handling
window.sendMessage = function() {
  const inputField = document.getElementById("user-input");
  const message = inputField.value.trim();
  if (!message) return;

  appendUserMessage(message);
  inputField.value = "";

  const preferences = {
    session_id: sessionId,
    artist_or_song: message
  };

  fetch(`${backendUrl}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preferences)
  })
  .then(res => res.json())
  .then(data => {
    appendBotMessage(data.response || "⚠️ Something went wrong.");
    if (data.spotify_url || data.preview_url) {
      updateSpotifyPreview(data);
    }
  })
  .catch(error => {
    console.error("API error:", error);
    appendBotMessage("⚠️ Sorry, something went wrong while contacting Moodify.");
  });
}

// Initial greeting on page load
window.onload = () => {
  fetch(`${backendUrl}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, artist_or_song: "hi" })
  })
  .then(res => res.json())
  .then(data => appendBotMessage(data.response))
  .catch(error => {
    console.error("API error:", error);
    appendBotMessage("⚠️ Sorry, something went wrong while contacting Moodify.");
  });
};

const sessionId = generateSessionId();

function generateSessionId() {
  return 'sess-' + Math.random().toString(36).substring(2, 10);
}

document.getElementById("user-input").addEventListener("keypress", function(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
});

function appendUserMessage(msg) {
  const chatBox = document.getElementById("chat-box");
  chatBox.innerHTML += `<p><strong>You:</strong> ${msg}</p>`;
  chatBox.scrollTop = chatBox.scrollHeight;
}

function updateSpotifyPreview(data) {
  const previewContainer = document.getElementById("spotify-preview");
  previewContainer.innerHTML = `
    <img src="${data.cover_art || ''}" alt="Album Art">
    <p><strong>${data.song || 'Unknown Song'}</strong> by ${data.artist || 'Unknown Artist'}</p>
    ${data.preview_url ? `<audio controls src="${data.preview_url}"></audio>` : ''}
    ${data.spotify_url ? `<a href="${data.spotify_url}" target="_blank">🎧 Listen on Spotify</a>` : ''}
  `;
}

function appendBotMessage(msg) {
  const chatBox = document.getElementById("chat-box");
  chatBox.innerHTML += `<p class="green-response"><strong>Moodify:</strong> ${msg}</p>`;
  chatBox.scrollTop = chatBox.scrollHeight;
}
