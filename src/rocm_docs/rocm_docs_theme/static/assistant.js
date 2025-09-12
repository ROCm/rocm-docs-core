// connection to server
const API_URL = window.CHATBOT_SOURCE;

const assistant = document.getElementById("assistant");
const assistantToggle = document.getElementById("assistant-toggle");
const assistantWindow = document.getElementById("assistant-window");

const clearButton = document.getElementById("chat-clear");
const maximizeButton = document.getElementById("chat-maximize");
const minimizeButton = document.getElementById("chat-minimize");
const closeButton = document.getElementById("chat-close");

const chatbox = document.getElementById("chat-body");

const userInput = document.getElementById("user-input");
const sendButton = document.getElementById("send-button");

const defaultInputHeight = userInput.scrollHeight;

const welcomeMessage
    = "<p>Welcome to the ROCm Documentation!</p>"
    + "<p>How can I assist you today?</p>";

const CHAT_HISTORY_DB = "ROCmChatDB";
const CHAT_HISTORY_STORE = "chat_history";

function groupParagraphs(text) {
    // group by newlines
    // remove all empty lines
    // wrap paragraphs
    return text
        .split(/\r?\n/)
        .filter(line => line.trim() !== "")
        .map(line => `<p>${line}</p>`)
        .join("");
}

function inlineCode(text) {
    return text
        .replace(/`([^`]+)`/g, (_, code) => `<code>${code}</code>`);
}

function createMessage(content, type, inputted = false) {
    const message = document.createElement("li");

    message.classList.add("chat-message", type);

    if (type === "outgoing" && inputted) {
        message.innerHTML = groupParagraphs(inlineCode(content));
    } else {
        message.innerHTML = content;
    }

    return message;
}

function setChatMessage(message, content) {
    message.innerHTML = content;
    chatbox.scrollTo(0, chatbox.scrollHeight);
}

function displayMessage(message) {
    chatbox.appendChild(message);
    chatbox.scrollTo(0, chatbox.scrollHeight);

    return message;
}

async function generateResponse(query) {
    try {
        const response = await fetch(API_URL + "/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                content: query
            })
        });

        if (!response.ok) {
            return "Sorry, the server could not be reached.";
        }

        const data = await response.json();
        return data.response;
    } catch (e) {
        return "Sorry, the server response could not be processed.";
    }
}

async function clearHistory() {
    try {
        const response = await fetch(API_URL + "/clear", {
            method: "POST"
        });
        return response.ok;
    } catch (e) {
        return false;
    }
}

async function sendMessage(input) {
    if (sendButton.disabled)
        return;

    sendButton.disabled = true;
    userInput.disabled = true;

    // clear input and display sent message
    userInput.value = "";
    userInput.style.height = `${defaultInputHeight}px`;

    const question = createMessage(input, "outgoing", true);

    displayMessage(question);
    await saveChatMessage(question, "outgoing");

    // display awaiting message
    const incoming = createMessage("<p>Awaiting...</p>", "incoming");
    displayMessage(incoming);

    // display the new generated response
    const response = await generateResponse(input);

    // set generated response, and then save it
    setChatMessage(incoming, response);
    await saveChatMessage(incoming, "incoming");

    sendButton.disabled = false;
    userInput.disabled = false;
    userInput.focus();
}

async function loadChat() {
    const messages = await getChatMessages();
    if (messages && messages.length > 0) {
        chatbox.innerHTML = "";
        displayMessage(createMessage(welcomeMessage, "incoming"));
        for (const msg of messages) {
            const message = createMessage(msg.message, msg.type);
            displayMessage(message);
        }
    } else {
        displayMessage(createMessage(welcomeMessage, "incoming"));
    }
}

async function clearChat() {
    sendButton.disabled = true;
    userInput.disabled = true;

    chatbox.innerHTML = "";
    const initialMessage = createMessage(welcomeMessage, "incoming");
    displayMessage(initialMessage);

    await clearHistory();
    await clearDatabase();

    sendButton.disabled = false;
    userInput.disabled = false;
}

async function openChatHistoryDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(CHAT_HISTORY_DB);

        // when creating new database
        request.onupgradeneeded = (event) => {
            const database = request.result;
            database.createObjectStore(
                CHAT_HISTORY_STORE,
                {
                    keyPath: "id",
                    autoIncrement: true
                }
            );
            return database;
        }

        request.onsuccess = (event) => {
            resolve(request.result);
        };

        request.onerror = (event) => {
            reject(request.error);
        };
    });
}

async function saveChatMessage(message, type) {
    const database = await openChatHistoryDatabase();
    const store = database
        .transaction(CHAT_HISTORY_STORE, "readwrite")
        .objectStore(CHAT_HISTORY_STORE);

    store.add({   
        type: type,
        message: message.innerHTML
    });
}

async function getChatMessages() {
    const database = await openChatHistoryDatabase();
    const store = await database
        .transaction(CHAT_HISTORY_STORE, "readonly")
        .objectStore(CHAT_HISTORY_STORE);

    const request = store.getAll();

    return new Promise((resolve, reject) => {
        request.onsuccess = (event) => {
            resolve(request.result); // array
        };

        request.onerror = (event) => {
            reject(request.error);
        };
    });
}

async function clearDatabase() {
    const database = await openChatHistoryDatabase();
    const store = database
        .transaction(CHAT_HISTORY_STORE, "readwrite")
        .objectStore(CHAT_HISTORY_STORE);

    const request = store.clear();

    return new Promise((resolve, reject) => {
        request.onsuccess = (event) => {
            resolve(request.result); // array
        };

        request.onerror = (event) => {
            reject(request.error);
        };
    });
}

window.addEventListener('DOMContentLoaded', loadChat);

document.addEventListener("mousedown", (event) => {
    if (assistantWindow.contains(event.target))
        return;

    if (assistant.classList.contains("fullscreen")) {
        assistant.classList.remove("fullscreen");
        return;
    }

    assistant.classList.remove("active");
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && assistant.classList.contains("fullscreen")) {
        assistant.classList.remove("fullscreen");
    }
});
    
assistantToggle.addEventListener("click", () => {
    assistant.classList.toggle("active");
});

closeButton.addEventListener("click", () => {
    assistant.classList.toggle("active");
});

maximizeButton.addEventListener("click", () => {
    assistant.classList.add("fullscreen");
});

minimizeButton.addEventListener("click", () => {
    assistant.classList.remove("fullscreen");
});

clearButton.addEventListener("click", () => {
    clearChat();
});

sendButton.addEventListener("click", () => {
    const message = userInput.value.trim();
    if (!message)
        return;

    sendMessage(message);
});

userInput.addEventListener("input", () => {
    userInput.style.height = `${defaultInputHeight}px`;
    userInput.style.height = `${userInput.scrollHeight}px`;
});

userInput.addEventListener("keydown", (e) => {
    if(e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();

        const message = userInput.value.trim();
        if (!message)
            return;

        sendMessage(message);
    }
});