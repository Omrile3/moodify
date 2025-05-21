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

  if (message.toLowerCase().includes("another") || message.toLowerCase().includes("change")) {
    handleCommand(message);
  } else {
    handlePreferences(message);
  }
}

function handlePreferences(message) {
  // Extract preferences using regex
  const genreMatch = message.match(/pop|rock|hip[- ]?hop|edm|latin/i);
  const moodMatch = message.match(/happy|calm|energetic|sad/i);
  const tempoMatch = message.match(/slow|medium|fast/i);
  const artistMatch = message.includes("by") ? message.split("by").pop().trim() : null;

  const preferences = {
    session_id: sessionId,
    genre: genreMatch ? genreMatch[0].toLowerCase() : null,
    mood: moodMatch ? moodMatch[0].toLowerCase() : null,
    tempo: tempoMatch ? tempoMatch[0].toLowerCase() : null,
    artist_or_song: artistMatch || null
  };

  // Ensure all keys are present to satisfy FastAPI model
  fetch(`${backendUrl}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preferences)
  })
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(data => {
      appendBotMessage(data.response || data.message);
      renderOptions(data.options || []);
    })
    .catch(err => {
      appendBotMessage("🚨 Error talking to Moodify. Try again.");
      console.error("Fetch error:", err);
    });
}

function handleCommand(command) {
  fetch(`${backendUrl}/command`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, command })
  })
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(data => {
      if (data.response) {
        appendBotMessage(data.response);
      } else if (data.message) {
        appendBotMessage(data.message);
      }
      renderOptions(data.options || []);
    })
    .catch(err => {
      appendBotMessage("🚨 Command failed. Please try again.");
      console.error("Command error:", err);
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
