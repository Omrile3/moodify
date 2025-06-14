const backendUrl = "https://moodify-backend-uj8d.onrender.com"; // Update this if testing locally or on a different deployment

const sessionId = generateSessionId();

window.sendMessage = function () {
  const inputField = document.getElementById("user-input");
  const message = inputField.value.trim();
  if (!message) return;

  appendUserMessage(message);
  inputField.value = "";

  const preferences = {
    session_id: sessionId,
    artist_or_song: message
  };

  showTypingIndicator();

  fetch(`${backendUrl}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preferences)
  })
    .then(res => res.json())
    .then(data => {
      const delay = calculateTypingDelay(data.response);
      setTimeout(() => {
        hideTypingIndicator();
        appendBotMessage(data.response || "Something went wrong.");
        updatePreferencesPanel(); // Update panel after bot response
      }, delay);
    })
    .catch(error => {
      console.error("API error:", error);
      hideTypingIndicator();
      appendBotMessage("⚠️ Sorry, something went wrong while contacting Moodify.");
      updatePreferencesPanel();
    });
};

// Initial greeting on page load
window.onload = () => {
  fetch(`${backendUrl}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, artist_or_song: "hi" })
  })
    .then(res => res.json())
    .then(data => {
      document.getElementById("chat-box").innerHTML = ""; // Ensure chat is empty
      appendBotMessage(data.response);
      updatePreferencesPanel(); // Show empty/default preferences at start
    })
    .catch(error => {
      console.error("API error:", error);
      appendBotMessage("⚠️ Sorry, something went wrong while contacting Moodify.");
      updatePreferencesPanel();
    });
};

function generateSessionId() {
  return 'sess-' + Math.random().toString(36).substring(2, 10);
}

document.getElementById("user-input").addEventListener("keypress", function (event) {
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

function appendBotMessage(msg) {
  const chatBox = document.getElementById("chat-box");
  chatBox.innerHTML += `<p class="green-response"><strong>Moodify:</strong> ${msg}</p>`;
  chatBox.scrollTop = chatBox.scrollHeight;
}

function showTypingIndicator() {
  const chatBox = document.getElementById("chat-box");
  const typing = document.createElement("p");
  typing.id = "typing-indicator";
  typing.innerHTML = `<em>Moodify is typing...</em>`;
  chatBox.appendChild(typing);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function hideTypingIndicator() {
  const typing = document.getElementById("typing-indicator");
  if (typing) typing.remove();
}

function calculateTypingDelay(text) {
  const wordCount = text.split(" ").length;
  const delayPerWord = 120; // ms
  return Math.min(3000, wordCount * delayPerWord);
}

window.resetSession = function () {
  showTypingIndicator();
  fetch(`${backendUrl}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId })
  })
    .then(res => res.json())
    .then(data => {
      hideTypingIndicator();

      // --- FULL RESET: clear chat, preferences, and input ---
      document.getElementById("chat-box").innerHTML = ""; // Clear all chat history

      document.getElementById("pref-genre").innerText = '—';
      document.getElementById("pref-mood").innerText = '—';
      document.getElementById("pref-tempo").innerText = '—';
      document.getElementById("pref-artist").innerText = '—';

      document.getElementById("user-input").value = ""; // Clear user input field

      appendBotMessage(data.response || "Session reset."); // Show reset greeting/message only
    })
    .catch(error => {
      hideTypingIndicator();
      appendBotMessage("⚠️ Sorry, something went wrong while resetting your session.");
      console.error("Reset error:", error);

      // Also reset panel in case backend fails
      document.getElementById("pref-genre").innerText = '—';
      document.getElementById("pref-mood").innerText = '—';
      document.getElementById("pref-tempo").innerText = '—';
      document.getElementById("pref-artist").innerText = '—';
      document.getElementById("user-input").value = "";
    });
};

// --- Preferences Panel Logic ---

function updatePreferencesPanel() {
  fetch(`${backendUrl}/session/${sessionId}`)
    .then(res => res.json())
    .then(data => {
      // Defensive defaults
      const genre = data.genre ? capitalize(data.genre) : '—';
      const mood = data.mood ? capitalize(data.mood) : '—';
      const tempo = data.tempo ? capitalize(data.tempo) : '—';
      const artist = data.artist_or_song ? capitalize(data.artist_or_song) : '—';

      document.getElementById("pref-genre").innerText = genre;
      document.getElementById("pref-mood").innerText = mood;
      document.getElementById("pref-tempo").innerText = tempo;
      document.getElementById("pref-artist").innerText = artist;
    })
    .catch(() => {
      // In case backend fails, clear to dashes
      document.getElementById("pref-genre").innerText = '—';
      document.getElementById("pref-mood").innerText = '—';
      document.getElementById("pref-tempo").innerText = '—';
      document.getElementById("pref-artist").innerText = '—';
    });
}

function capitalize(s) {
  if (typeof s !== "string") return s;
  return s.length > 0 ? s[0].toUpperCase() + s.slice(1) : s;
}
