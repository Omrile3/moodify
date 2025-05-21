const backendUrl = "https://moodify-backend-uj8d.onrender.com"; 
const sessionId = generateSessionId();

function generateSessionId() {
  return 'sess-' + Math.random().toString(36).substring(2, 10);
}

function sendMessage() {
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
  });
}

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
