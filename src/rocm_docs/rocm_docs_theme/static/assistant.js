// connection to server
let socket;
let awaitingResponse = false;

const assistant = document.getElementById("assistant");
const assistantToggle = document.getElementById("assistant-toggle");
const chatbox = document.getElementById("chat-body");
const userInput = document.getElementById("user-input");
const sendButton = document.getElementById("send-button");
const closeButton = document.getElementById("chat-close");
const assistantWindow = document.getElementById("assistant-window");
const maximizeButton = document.getElementById("chat-maximize");
const minimizeButton = document.getElementById("chat-minimize");

const defaultInputHeight = userInput.scrollHeight;

function createChatMessage(message, incoming) {
    const chatMessage = document.createElement("li");

    const messageText = document.createElement("p");
    chatMessage.appendChild(messageText);

    let messageType = incoming ? "incoming" : "outgoing";
    chatMessage.classList.add("chat-message", messageType);

    messageText.textContent = message;

    return chatMessage;
}

function setChatMessage(message, content) {
    // message: <li> element, content: string
    const p = message.querySelector('p');
    if (p) {
        p.textContent = content;

        chatbox.scrollTo(0, chatbox.scrollHeight);
    }
}

function displayMessage(input, incoming) {
    let message = createChatMessage(input, incoming);

    chatbox.appendChild(message);
    chatbox.scrollTo(0, chatbox.scrollHeight);

    return message;
}

function connectWebSocket() {
    console.log(window.CHATBOT_SOURCE);
    const ws = new WebSocket(window.CHATBOT_SOURCE);
    ws.onclose = () => {
        setTimeout(connectWebSocket, 5000);
    };
    ws.onerror = () => {
        ws.close();
    };
    return ws;
}

function getWebSocket() {
    if (!socket || socket.readyState === WebSocket.CLOSED) {
        socket = connectWebSocket();
    }
    return socket;
}

async function generateResponse(query) {
    return new Promise((resolve) => {
        let socket = getWebSocket();

        function parseResponse(event) {
            try {
                const data = JSON.parse(event.data);
                resolve(data.response);
            } catch (e) {
                resolve("Sorry, the server response could not be processed.");
            }
            socket.removeEventListener('message', parseResponse);
        }

        socket.addEventListener('message', parseResponse);
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(query);
        } else if (socket.readyState === WebSocket.CONNECTING) {
            socket.addEventListener('open', function handleOpen() {
                socket.send(query);
                socket.removeEventListener('open', handleOpen);
            });
        }

        // if socket closes before response, handle as error
        socket.addEventListener('close', () => {
            resolve("Sorry, the server could not be reached.");
            socket.removeEventListener('message', parseResponse);
        }, { once: true });
    });
}

async function sendMessage(input) {
    if (awaitingResponse)
        return;

    awaitingResponse = true;
    sendButton.disabled = true;
    userInput.disabled = true;

    // clear input and display sent message
    userInput.value = "";
    userInput.style.height = `${defaultInputHeight}px`;
    displayMessage(input, false);

    // display awaiting message
    let incoming = displayMessage("Awaiting...", true);

    // display the new generated response
    let response = await generateResponse(input);

    setChatMessage(incoming, response);

    awaitingResponse = false;
    sendButton.disabled = false;
    userInput.disabled = false;
    userInput.focus();
}

// initialize server connection on load
connectWebSocket();

document.addEventListener("mousedown", (event) => {
    if (assistantWindow.contains(event.target))
        return;

    if (assistant.classList.contains("fullscreen")) {
        assistant.classList.remove("fullscreen");
        return;
    }

    assistant.classList.remove("active");
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

sendButton.addEventListener("click", () => {
    if (awaitingResponse) return;
    const message = userInput.value.trim();
    if (!message) return;
    sendMessage(message);
});

userInput.addEventListener("input", () => {
    userInput.style.height = `${defaultInputHeight}px`;
    userInput.style.height = `${userInput.scrollHeight}px`;
});

userInput.addEventListener("keydown", (e) => {
    if(e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();

        if (awaitingResponse)
            return;

        const message = userInput.value.trim();
        if (!message)
            return;

        sendMessage(message);
    }
});
