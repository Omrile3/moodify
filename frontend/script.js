const backendUrl = "https://moodify-backend-uj8d.onrender.com"; // Update if testing locally/different deployment

const sessionId = generateSessionId();

// Monkey-patch window.handleBotReply so backend HTML buttons always work!
window.handleBotReply = function (msg) {
  appendUserMessage(msg, true);
  showTypingIndicator();

  fetch(`${backendUrl}/command`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, command: msg })
  })
    .then(res => res.json())
    .then(data => {
      const delay = calculateTypingDelay(data.response);
      setTimeout(() => {
        hideTypingIndicator();
        appendBotMessage(data.response || "Something went wrong.");
        updatePreferencesPanel();
      }, delay);
    })
    .catch(error => {
      console.error("API error:", error);
      hideTypingIndicator();
      appendBotMessage("⚠️ Sorry, something went wrong while contacting Moodify.");
      updatePreferencesPanel();
    });
};

// --- Existing code ---

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
        updatePreferencesPanel(); // Always fetch sidebar from backend after bot response
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
  document.getElementById("chat-box").innerHTML = ""; // Ensure chat is empty
  fetch(`${backendUrl}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, artist_or_song: "hi" })
  })
    .then(res => res.json())
    .then(data => {
      appendBotMessage(data.response);
      updatePreferencesPanel();
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

function appendUserMessage(msg, isButton) {
  const chatBox = document.getElementById("chat-box");
  // If message is from a button, don't prepend "You:"
  if (isButton) {
    chatBox.innerHTML += `<p><strong>You:</strong> <span class="user-btn-msg">${msg}</span></p>`;
  } else {
    chatBox.innerHTML += `<p><strong>You:</strong> ${msg}</p>`;
  }
  chatBox.scrollTop = chatBox.scrollHeight;
}

// PATCH: Spotify strip works for any Spotify link in bot message (HTML, text, or both)
function appendBotMessage(msgOrObj) {
  const chatBox = document.getElementById("chat-box");
  let msg = msgOrObj;
  let spotifyUrl = null;

  // If backend sends an object instead of string (future-proof):
  if (typeof msgOrObj === "object" && msgOrObj !== null) {
    msg = msgOrObj.response || msgOrObj.text || "";
    if (msgOrObj.spotify_url) spotifyUrl = msgOrObj.spotify_url;
  } else {
    // Try to extract spotify_url from HTML in message
    const spotifyMatch = msg && msg.match(/https:\/\/open\.spotify\.com\/track\/([a-zA-Z0-9]+)/);
    if (spotifyMatch) {
      spotifyUrl = `https://open.spotify.com/track/${spotifyMatch[0].split("/").pop()}`;
    }
  }

  let html = `<p class="green-response"><strong>Moodify:</strong> ${msg}</p>`;

  // --- Always embed if we have a valid spotifyUrl ---
  if (spotifyUrl) {
    // Only take the track ID if present
    const idMatch = spotifyUrl.match(/track\/([a-zA-Z0-9]+)/);
    if (idMatch) {
      html += `
        <div class="spotify-embed">
          <iframe style="border-radius:12px;margin-top:4px;" src="https://open.spotify.com/embed/track/${idMatch[1]}" width="100%" height="80" frameborder="0" allow="autoplay; clipboard-write; encrypted-media; picture-in-picture" allowfullscreen></iframe>
        </div>
      `;
    }
    // Remove redundant Listen on Spotify plain links from message text
    html = html.replace(/<a [^>]+>(Listen on Spotify)?<\/a>/ig, '').replace(/https:\/\/open\.spotify\.com\/track\/[a-zA-Z0-9]+/g, '');
    // Re-append bot name and message without redundant link
    html = `<p class="green-response"><strong>Moodify:</strong> ${msg.replace(/<a [^>]+>(Listen on Spotify)?<\/a>/ig, '').replace(/https:\/\/open\.spotify\.com\/track\/[a-zA-Z0-9]+/g, '')}</p>` + html.split('</p>')[1];
  }

  chatBox.innerHTML += html;
  chatBox.scrollTop = chatBox.scrollHeight;

  setTimeout(activateAllBackendButtons, 0);
}

function activateAllBackendButtons() {
  const buttons = document.querySelectorAll('button[onclick^="window.handleBotReply"]');
  buttons.forEach(btn => {
    // Only patch if not already patched (avoid multiple listeners)
    if (!btn.dataset.patched) {
      const cmdMatch = btn.getAttribute('onclick').match(/window\.handleBotReply\(['"](.+?)['"]\)/);
      if (cmdMatch) {
        btn.onclick = function () { window.handleBotReply(cmdMatch[1]); };
        btn.dataset.patched = "true";
      }
    }
  });
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
  if (!text) return 500;
  const wordCount = text.split(" ").length;
  const delayPerWord = 120; // ms
  return Math.min(3000, wordCount * delayPerWord);
}

// --- PATCHED RESET: reload page after backend reset ---
window.resetSession = function () {
  showTypingIndicator();
  fetch(`${backendUrl}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId })
  })
    .then(res => res.json())
    .then(data => {
      // After backend confirms, reload the page for a full fresh state
      window.location.reload();
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
