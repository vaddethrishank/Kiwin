(function () {
  const SCRIPT_TAG = document.currentScript || document.querySelector('script[data-agent-id]');
  const AGENT_ID = SCRIPT_TAG.getAttribute('data-agent-id');
  const PRIMARY_COLOR = SCRIPT_TAG.getAttribute('data-color') || '#000';
  const ICON_SIZE = SCRIPT_TAG.getAttribute('data-icon-size') || '60';
  const POSITION = SCRIPT_TAG.getAttribute('data-position') || 'right'; // 'right' or 'left'
  const API_BASE_URL = SCRIPT_TAG.getAttribute('data-api-url') || "http://localhost:8000";
  const API_URL = `${API_BASE_URL}/api/v1/public/chat`;

  if (!AGENT_ID) {
    console.error("Kiwin Widget: Agent ID is missing.");
    return;
  }

  // Styles
  const STYLES = `
    .kiwin-bubble {
      position: fixed;
      bottom: 20px;
      ${POSITION === 'left' ? 'left: 20px;' : 'right: 20px;'}
      width: ${ICON_SIZE}px;
      height: ${ICON_SIZE}px;
      background-color: ${PRIMARY_COLOR};
      border-radius: 50%;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      transition: transform 0.2s;
    }
    .kiwin-bubble:hover { transform: scale(1.05); }
    .kiwin-bubble svg { width: ${ICON_SIZE * 0.5}px; height: ${ICON_SIZE * 0.5}px; fill: white; }
    
    .kiwin-chat-window {
      position: fixed;
      bottom: 90px;
      ${POSITION === 'left' ? 'left: 20px;' : 'right: 20px;'}
      width: 350px;
      height: 500px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
      z-index: 9999;
      display: none;
      flex-direction: column;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      border: 1px solid #eee;
    }
    .kiwin-header {
      padding: 15px;
      background: ${PRIMARY_COLOR};
      color: white;
      font-weight: 600;
      display: flex;
      justify-content: space-between;
      align-items: center;
      min-height: 50px;
    }
    .kiwin-close { cursor: pointer; font-size: 20px; }
    .kiwin-messages {
      flex: 1;
      padding: 15px;
      overflow-y: auto;
      background: #f9f9f9;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .kiwin-input-area {
      padding: 10px;
      border-top: 1px solid #eee;
      display: flex;
      background: white;
    }
    .kiwin-input {
      flex: 1;
      border: 1px solid #ddd;
      border-radius: 20px;
      padding: 8px 12px;
      outline: none;
    }
    .kiwin-send-btn {
      margin-left: 8px;
      width: 36px;
      height: 36px;
      border: none;
      background: ${PRIMARY_COLOR};
      border-radius: 50%;
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.1s;
    }
    .kiwin-send-btn:hover { transform: scale(1.05); }
    .kiwin-send-btn:active { transform: scale(0.95); }
    .kiwin-send-btn svg { width: 18px; height: 18px; fill: white; }
    .kiwin-msg {
      max-width: 80%;
      padding: 8px 12px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.4;
    }
    .kiwin-msg.user {
      align-self: flex-end;
      background: ${PRIMARY_COLOR};
      color: white;
      border-bottom-right-radius: 2px;
    }
    .kiwin-msg.ai {
      align-self: flex-start;
      background: #e5e5e5;
      color: black;
      border-bottom-left-radius: 2px;
    }
  `;

  // Inject Styles
  const styleSheet = document.createElement("style");
  styleSheet.innerText = STYLES;
  document.head.appendChild(styleSheet);

  // Containers
  const bubble = document.createElement("div");
  bubble.className = "kiwin-bubble";
  bubble.innerHTML = `<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"></path></svg>`;

  const chatWindow = document.createElement("div");
  chatWindow.className = "kiwin-chat-window";

  // Header span starts empty
  chatWindow.innerHTML = `
    <div class="kiwin-header">
      <span></span>
      <span class="kiwin-close">&times;</span>
    </div>
    <div class="kiwin-messages" id="kiwin-messages"></div>
    <div class="kiwin-input-area">
      <input type="text" class="kiwin-input" placeholder="Type a message..." />
      <button class="kiwin-send-btn">
        <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg>
      </button>
    </div>
  `;

  document.body.appendChild(bubble);
  document.body.appendChild(chatWindow);

  // State
  let isOpen = false;
  let sessionId = localStorage.getItem("kiwin_session_id");
  let agentName = "AI Assistant";
  // Fixed: Default simplified welcome message
  let welcomeMessage = "Hello! How can I help you today?";

  if (!sessionId) {
    sessionId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
    localStorage.setItem("kiwin_session_id", sessionId);
  }

  // Elements
  const closeBtn = chatWindow.querySelector(".kiwin-close");
  const headerTitle = chatWindow.querySelector(".kiwin-header span:first-child");
  const input = chatWindow.querySelector(".kiwin-input");
  const sendBtn = chatWindow.querySelector(".kiwin-send-btn");
  const messagesDiv = chatWindow.querySelector(".kiwin-messages");

  // Fetch Agent Details (Logic: Update Header Name only)
  async function initWidget() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/public/agents/${AGENT_ID}`);
      if (res.ok) {
        const data = await res.json();

        // 1. Set Name in Header
        if (data.name) {
          agentName = data.name;
          headerTitle.innerText = `Chat with ${agentName}`;
        } else {
          headerTitle.innerText = "Chat with AI Assistant";
        }
      } else {
        headerTitle.innerText = "Chat with AI Assistant";
      }
    } catch (e) {
      console.error("Kiwin Widget: Failed to load agent details.", e);
      headerTitle.innerText = "Chat with AI Assistant";
    }
  }

  // Initialize immediately
  initWidget();

  // Toggle
  function toggleChat() {
    isOpen = !isOpen;
    chatWindow.style.display = isOpen ? "flex" : "none";

    if (isOpen) {
      input.focus();

      // Show welcome message if empty
      if (messagesDiv.children.length === 0) {
        addMessage(welcomeMessage, "ai");
      }
    }
  }

  bubble.onclick = toggleChat;
  closeBtn.onclick = toggleChat;

  // Append Message
  function addMessage(text, role) {
    const div = document.createElement("div");
    div.className = `kiwin-msg ${role}`;
    div.innerText = text;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  // Send Message
  async function sendMessage(text) {
    if (!text.trim()) return;
    addMessage(text, "user");
    input.value = "";
    input.disabled = true;

    // Create AI Placeholder
    const aiDiv = document.createElement("div");
    aiDiv.className = "kiwin-msg ai";
    aiDiv.innerText = "...";
    messagesDiv.appendChild(aiDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_id: AGENT_ID,
          message: text,
          session_id: sessionId
        })
      });

      if (!response.ok) throw new Error("API Error");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiText = "";
      aiDiv.innerText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        aiText += chunk;
        aiDiv.innerText = aiText;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
      }

    } catch (e) {
      aiDiv.innerText = "Error: Could not reach agent.";
    } finally {
      input.disabled = false;
      input.focus();
    }
  }

  // Input Listeners
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage(input.value);
  });

  sendBtn.addEventListener("click", () => sendMessage(input.value));

})();
