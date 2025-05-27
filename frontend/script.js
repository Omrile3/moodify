const backendUrl = "https://moodify-backend-uj8d.onrender.com"; // Update this if testing locally or on a different deployment

const sessionId = generateSessionId();

function generateSessionId() {
  return 'sess-' + Math.random().toString(36).substring(2, 10);
}

// Send message from user
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
  })
  .catch(error => {
    console.error("API error:", error);
    appendBotMessage("⚠️ Sorry, something went wrong while contacting Moodify.");
  });
};

// Reset preferences (but not chat history)
window.resetSession = function() {
  fetch(`${backendUrl}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, command: "reset" })
  })
  .then(res => res.json())
  .then(data => {
    appendBotMessage(data.response || "Preferences have been reset.");
  })
  .catch(error => {
    console.error("API error:", error);
    appendBotMessage("⚠️ Couldn't reset Moodify session.");
  });
};

// Load greeting on page load
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

// Handle Enter key
document.getElementById("user-input").addEventListener("keypress", function(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
});

// Append chat lines
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
