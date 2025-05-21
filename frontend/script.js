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

  // Decide if this is a preference input or command
  if (message.toLowerCase().includes("another") || message.toLowerCase().includes("change")) {
    handleCommand(message);
  } else {
    handlePreferences(message);
  }
}

function handlePreferences(message) {
  // Basic NLP parsing (improve as needed)
  const preferences = {
    session_id: sessionId,
    genre: message.match(/pop|rock|hip[- ]?hop|edm|latin/i)?.[0],
    mood: message.match(/happy|calm|energetic|sad/i)?.[0],
    tempo: message.match(/slow|medium|fast/i)?.[0],
    artist_or_song: message.includes("by") ? message.split("by").pop().trim() : null
  };

  fetch(`${backendUrl}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preferences)
  })
  .then(res => res.json())
  .then(data => {
    appendBotMessage(data.response || data.message);
    renderOptions(data.options || []);
  });
}

function handleCommand(command) {
  fetch(`${backendUrl}/command`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, command })
  })
  .then(res => res.json())
  .then(data => {
    if (data.response) {
      appendBotMessage(data.response);
    } else if (data.message) {
      appendBotMessage(data.message);
    }
    renderOptions(data.options || []);
  });
}

function appendUserMessage(msg) {
  const chatBox = document.getElementById("chat-box");
  chatBox.innerHTML += `<p><strong>You:</strong> ${msg}</p>`;
  chatBox.scrollTop = chatBox.scrollHeight;
}

function appendBotMessage(msg) {
  const chatBox = document.getElementById("chat-box");
  chatBox.innerHTML += `<p><strong>Moodify:</strong> ${msg}</p>`;
  chatBox.scrollTop = chatBox.scrollHeight;
}

function renderOptions(options) {
  const container = document.getElementById("quick-options");
  container.innerHTML = "";
  options.forEach(opt => {
    const btn = document.createElement("button");
    btn.innerText = opt;
    btn.onclick = () => {
      document.getElementById("user-input").value = opt;
      sendMessage();
    };
    container.appendChild(btn);
  });
}
