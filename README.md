Here is the comprehensive API documentation for the **LLM Session API**.

---

# LLM Session API Documentation

## Overview
The **LLM Session API** is a unified interface that automates interactions with major web-based LLM providers (ChatGPT, Claude, and Google AI Studio/Gemini). 

Unlike official APIs that charge per token, this service runs headless browser instances to interact with the free or paid web tiers of these services using your personal Google credentials. It provides a standardized RESTful API to manage sessions, send prompts, and handle conversation chains.

**Current Version:** 1.0.0  
**Base URL:** `http://localhost:8080` (Default Docker configuration)

---

## 🚀 Quick Start

### Prerequisites
*   Docker & Docker Compose
*   A Google Account (used for SSO login across all providers)

### Installation
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/llm-session-api.git
    cd llm-session-api
    ```

2.  **Configure Credentials:**
    Copy the example environment file and add your Google credentials.
    ```bash
    cp .env.example .env
    # Edit .env and set GOOGLE_EMAIL and GOOGLE_PASSWORD
    ```

3.  **Start the Service:**
    ```bash
    docker-compose up --build -d
    ```
    *Note: The service takes roughly 15-30 seconds to initialize as it launches generic X11 displays and performs login checks for all providers in the background.*

---

## 🔐 Authentication & Security

### API Security
**Current Status:** Public (Internal Network)
The current version of the API **does not** implement API Key authentication on the endpoints (`/generate`, etc.). It is designed to run within a private network (e.g., behind a firewall or inside a Docker network). 
*   **Recommendation:** Do not expose port `8080` to the public internet without a reverse proxy (Nginx/Traefik) handling authentication.

### Provider Authentication
The service uses the credentials provided in `.env` to log in to OpenAI, Anthropic, and Google via their web interfaces.
*   **Session Persistence:** Cookies are stored in the Docker volume `llm_session_data`. This ensures the bots remain logged in across container restarts to minimize suspicious login activity checks.

---

## 📡 API Reference

### 1. Health Check
Verifies the service is running and reports which providers are initialized.

*   **Endpoint:** `GET /health`
*   **Auth:** None

#### Response
```json
{
  "status": "ok",
  "providers": [
    "chatgpt",
    "aistudio",
    "claude"
  ]
}
```

---

### 2. Generate Content
The core endpoint to send prompts to a specific LLM provider. Supports both single prompts and conversation chains.

*   **Endpoint:** `POST /generate`
*   **Content-Type:** `application/json`

#### Request Body Parameters

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `provider` | `string` (enum) | No | `chatgpt` | Target LLM. Options: `chatgpt`, `claude`, `aistudio`. |
| `prompt` | `string` OR `list[string]` | **Yes** | - | The input text. Pass a **String** for a single question. Pass a **List** of strings to simulate a conversation chain (context is preserved for the duration of the list processing). |

#### Example 1: Single Prompt
**Request:**
```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "claude",
    "prompt": "Explain quantum computing in one sentence."
  }'
```

**Response:**
```json
{
  "status": "success",
  "provider": "claude",
  "mode": "single",
  "result": "Quantum computing uses quantum mechanics to process information in ways that standard computers cannot, allowing for potentially exponential speedups in specific complex calculations."
}
```

#### Example 2: Conversation Chain
This is useful if you need to set context before asking the actual question.

**Request:**
```json
{
  "provider": "chatgpt",
  "prompt": [
    "I am going to provide a snippet of code. Reply only with 'OK' if you understand.",
    "print('Hello World')",
    "Rewrite the code above in C++."
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "provider": "chatgpt",
  "mode": "chain",
  "result": [
    "OK",
    "OK", 
    "#include <iostream>\n\nint main() {\n    std::cout << \"Hello World\" << std::endl;\n    return 0;\n}"
  ]
}
```

---

### 3. Reset Session
Forces the browser instance for a specific provider to close and reset. Use this if a provider becomes unresponsive or "hallucinates" excessively.

*   **Endpoint:** `DELETE /session/{provider}`
*   **Path Parameters:**
    *   `provider`: `chatgpt`, `claude`, or `aistudio`.

#### Example
```bash
curl -X DELETE http://localhost:8080/session/claude
```

#### Response
```json
{
  "message": "claude browser closed."
}
```
*Note: The next time a request is sent to Claude, the system will automatically re-launch the browser and re-authenticate.*

---

## ⚠️ Limitations & Queue Behavior

### Concurrency Model
Due to the nature of browser automation (memory usage and DOM manipulation), this service uses a **Single Worker Queue** per provider.

1.  **Serialized Requests:** If you send 5 requests to `chatgpt` simultaneously, they will be processed one by one.
2.  **Parallel Providers:** Requests to `chatgpt` do **not** block requests to `claude`. They run in separate threads.
3.  **Timeout:** If a prompt takes too long, the internal automation may throw an exception.

### Rate Limiting
While the API itself does not enforce rate limits, the underlying providers (OpenAI, Anthropic) do.
*   **Risk:** Sending requests too fast may trigger "Too many requests" errors on the web interface or CAPTCHA challenges.
*   **Recommendation:** Implement a slight delay between requests in your client application.

---

## 🐛 Error Handling

The API returns standard HTTP status codes.

| Code | Status | Description |
| :--- | :--- | :--- |
| `200` | OK | Successful generation. |
| `400` | Bad Request | Invalid provider selected or malformed JSON. |
| `422` | Validation Error | Missing required fields (e.g., empty `prompt`). |
| `500` | Internal Server Error | Automation failure (e.g., Browser crashed, Element not found, Login failed). |

**Error Response Body:**
```json
{
  "detail": "Automation failed: Timeout waiting for response element."
}
```

---

## 💻 Client Code Examples

### Python (Requests)
```python
import requests

API_URL = "http://localhost:8080/generate"

def ask_llm(provider, text):
    payload = {
        "provider": provider,
        "prompt": text
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"[{data['provider']}] Response:\n{data['result']}")
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e.response.text}")

# Usage
ask_llm("chatgpt", "Write a haiku about APIs.")
```

### JavaScript (Node/Fetch)
```javascript
const askLLM = async (provider, prompt) => {
  const response = await fetch('http://localhost:8080/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ provider, prompt })
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail);
  }

  const data = await response.json();
  return data.result;
};

// Usage
askLLM('aistudio', 'List 3 generic naming conventions.')
  .then(console.log)
  .catch(console.error);
```

---

## 🛠 Troubleshooting

1.  **`500 Internal Server Error` on first request:**
    *   The service might still be initializing. Check the logs (`docker-compose logs -f`).
    *   Wait for the log message: `All initialization batches finished`.

2.  **"Provider not active" error:**
    *   Ensure the `.env` file has correct Google Credentials.
    *   Check logs to see if the login failed for that specific provider during startup.

3.  **Xvfb / Display Errors:**
    *   The Dockerfile includes a fix for Xvfb locks. If this persists, restart the container: `docker-compose restart`.