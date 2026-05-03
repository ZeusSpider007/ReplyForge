# 🔥 ReplyForge

> **Forge replies that don't sound like AI.**

ReplyForge is a local AI web application that turns any Twitter/X post into three sharp, human-sounding reply suggestions — **Professional**, **Bold**, and **Witty** — using a local LLM through Ollama. Everything runs on your machine. No cloud, no API keys, no telemetry.

![ReplyForge UI](https://img.shields.io/badge/Built%20for-Apple%20Silicon-black?style=flat-square&logo=apple)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/Powered%20by-Ollama-black?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

Made by [@NayanUnfiltered](https://x.com/NayanUnfiltered)

---

## What it does

- Paste any tweet or topic into the composer
- Click **Forge replies** (or press `⌘ + Enter`)
- Get 3 ready-to-post reply options in seconds:

| Style | Description |
|---|---|
| ◆ **Professional** | Thoughtful, insightful. Sounds like a senior practitioner who has seen this before. |
| ▲ **Bold** | Confident, opinionated, willing to push back. Takes a clear stance. |
| ✦ **Witty** | Light humor and clever phrasing. Earned wit, not a forced joke. |

- **Copy** any reply to clipboard or **Post on X** directly (opens the tweet intent URL)
- **Web context toggle** — searches DuckDuckGo before generating so replies are grounded in current events (no API key needed)
- **Model switcher** — swap between any locally installed text model per-request from a dropdown in the composer
- **Model Manager** — load and unload Ollama models directly from the UI, with live RAM/VRAM usage, works on Mac and Windows

---

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Backend | [FastAPI](https://fastapi.tiangolo.com/) + Python 3.11 | Async-first, Pydantic validation, minimal boilerplate |
| AI engine | [Ollama](https://ollama.com/) | Local LLM inference, Apple Silicon native (Metal acceleration) |
| LLM transport | [httpx](https://www.python-httpx.org/) | Async HTTP, full timeout/cancellation control |
| Structured output | Ollama `format: "json"` | Forces the model to return valid JSON — single call for all 3 replies |
| Web search | [ddgs](https://github.com/deedy5/duckduckgo_search) | Free, no API key, injects live context into the prompt |
| HTML parsing | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) | Strips HTML from search snippets before injecting as context |
| Frontend | Vanilla HTML + JavaScript + [Tailwind CSS](https://tailwindcss.com/) (CDN) | No build step, single file, instant iteration |
| Config | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | `.env` file → typed settings, zero boilerplate |
| Server | [Uvicorn](https://www.uvicorn.org/) | ASGI server, hot reload in development |

The frontend is served as a static file by the same FastAPI process — no separate dev server, no Node.js required.

---

## How the AI works

### Prompt architecture

The system is built around two prompt layers defined in [`backend/prompts.py`](backend/prompts.py):

**1. `SYSTEM_PROMPT` — the persona**

Sets a sharp, opinionated Twitter voice. Bans all AI-sounding patterns ("Great take", "As an AI", em-dashes, excessive hedging). Forces JSON output in the exact schema the backend expects.

**2. `STYLE_BRIEF` — the task**

Injected at the start of every user message. Defines what "professional", "bold", and "witty" mean concretely. Reminds the model about the 280-character hard limit.

**3. Web context (optional)**

When the web toggle is enabled, the backend runs a DuckDuckGo search using the first 120 characters of the post as the query. The top 4 results (title + snippet + URL) are prepended to the user message before sending to Ollama, letting the model reference current information. Source links are shown below the reply cards in the UI.

### Why one model call instead of three

Rather than making 3 separate API calls (one per style), ReplyForge uses Ollama's `format: "json"` parameter to get all 3 replies in a single structured response:

```json
{
  "replies": [
    { "style": "professional", "text": "..." },
    { "style": "bold",         "text": "..." },
    { "style": "witty",        "text": "..." }
  ]
}
```

This is **3× faster** than parallel calls and simpler to implement. The parser in `main.py` handles models that ignore `format: "json"` and still wrap output in markdown fences.

### Reply quality rules enforced in the prompt

- Under 280 characters — hard limit, verified server-side and truncated if exceeded
- No generic openers ("Great point!", "Absolutely!")
- No hashtags unless genuinely useful
- At most one emoji, only if it earns its place
- No em-dashes, no "It's not X, it's Y" constructions (classic AI tells)
- Lead with the strongest line — no warm-up sentences

---

## Project structure

```
ReplyForge/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, all API endpoints, Ollama transport, JSON parsing
│   ├── config.py        # Env-driven settings via pydantic-settings
│   ├── prompts.py       # SYSTEM_PROMPT + STYLE_BRIEF (edit this to tune the persona)
│   └── web.py           # DuckDuckGo search + HTML stripping for web context
├── frontend/
│   └── index.html       # Complete UI — single file, no build step
├── requirements.txt
├── .env.example
├── ReplyForge.command   # Double-click launcher for macOS
└── README.md
```

---

## Requirements

- macOS (Apple Silicon M1/M2/M3/M4 recommended — runs on Intel too) or Windows
- Python 3.11 or newer
- [Ollama](https://ollama.com/) installed
- At least one text-generation model pulled (see below)

---

## Installation

### Step 1 — Install Ollama

**macOS:**
```bash
brew install ollama
```
Or download the macOS app from [ollama.com](https://ollama.com) if you prefer a menu bar icon.

**Windows:**
Download and run the installer from [ollama.com/download](https://ollama.com/download).

### Step 2 — Pull a model

```bash
ollama pull llama3.1:8b
```

**Recommended models** (ranked by reply quality):

| Model | Size | Notes |
|---|---|---|
| `qwen2.5:14b` | ~9 GB | Best writer at this size, recommended |
| `phi4:14b` | ~9 GB | Microsoft, strong reasoning + sharp writing |
| `gemma3:12b` | ~8 GB | Google, very human-sounding output |
| `llama3.1:8b` | ~5 GB | Default, good quality, fastest |
| `mistral:7b` | ~4 GB | Lightweight alternative |

> The model dropdown in the UI only shows **text-generation models** — vision, embedding, whisper, and other non-text models are automatically filtered out.

### Step 3 — Clone and set up Python

```bash
git clone https://github.com/your-username/ReplyForge.git
cd ReplyForge

python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### Step 4 — Configure (optional)

```bash
cp .env.example .env
```

Open `.env` to change defaults:

```env
OLLAMA_HOST=http://127.0.0.1:11434
MODEL=llama3.1:8b
OLLAMA_TIMEOUT=60
TEMPERATURE=0.85
TOP_P=0.9
HOST=127.0.0.1
PORT=8000
```

Default values work out of the box — this step is only needed if you want a different default model or port.

---

## Running the app

### Option A — Double-click launcher (macOS)

Double-click **`ReplyForge.command`** in Finder.

It will:
1. Check if Ollama is already running and start it if not
2. Activate the Python virtual environment
3. Start the FastAPI server
4. Wait until the server is healthy
5. Open `http://127.0.0.1:8000` in your browser automatically

> **First launch only:** macOS may show "can't be opened because it's from an unidentified developer." Right-click → **Open** → **Open** to whitelist it permanently.

### Option B — Terminal (macOS / Windows)

```bash
# Terminal 1: start Ollama (skip if using the macOS/Windows app)
ollama serve

# Terminal 2: start ReplyForge
cd ReplyForge
source .venv/bin/activate        # macOS
# .venv\Scripts\activate         # Windows
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Usage

1. **Paste a tweet** into the composer, or write out what you want to reply to
2. **Select a model** from the dropdown (auto-populated from your Ollama library, vision/embed models excluded)
3. Optionally **enable Web context** to ground the reply in current search results
4. Press `⌘ + Enter` (Mac) / `Ctrl + Enter` (Windows) or click **Forge replies**
5. Three reply cards appear — **Copy** to clipboard or **Post on X** to open the tweet intent

The status pill in the top-right shows whether Ollama is running and the configured model is installed.

---

## Model Manager

The **Models** button in the top nav opens a panel that shows all your installed models and their current memory state:

- 🟢 **Green dot** — model is currently loaded in RAM/VRAM
- ⚫ **Grey dot** — model is installed but not loaded
- Memory usage (RAM and VRAM) is shown for loaded models
- **Unload** — evicts the model from memory immediately, freeing RAM/VRAM
- **Load** — pre-warms the model into memory for faster first generation
- A badge on the Models button shows how many models are currently loaded
- Works on both **Mac and Windows** via the Ollama API — no OS process killing

---

## Configuration reference

All settings live in `.env` (copied from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `MODEL` | `llama3.1:8b` | Default model (can be overridden per-request in the UI) |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama daemon address |
| `OLLAMA_TIMEOUT` | `60` | Per-request timeout in seconds |
| `TEMPERATURE` | `0.85` | Higher = more creative / unpredictable |
| `TOP_P` | `0.9` | Nucleus sampling threshold |
| `HOST` | `127.0.0.1` | Web server bind address |
| `PORT` | `8000` | Web server port |

---

## Tuning the AI persona

The persona lives entirely in [`backend/prompts.py`](backend/prompts.py). There are two variables to edit:

**`SYSTEM_PROMPT`** — controls the voice and hard rules. Edit this to change the personality, add domain focus (e.g. "you specialize in fintech Twitter"), or adjust constraints.

**`STYLE_BRIEF`** — defines what professional / bold / witty mean for the task. Edit this to change what each style produces, add a fourth style, or change the output format.

Changes take effect on the next request with no restart needed (uvicorn hot-reloads on save).

---

## API reference

### `GET /api/health`

Returns Ollama status and whether the configured model is installed.

```json
{
  "status": "ok",
  "ollama": "running",
  "model": "llama3.1:8b",
  "model_installed": true,
  "installed_models": ["llama3.1:8b", "qwen2.5:14b"]
}
```

### `GET /api/models`

Returns all locally installed text-generation models. Vision, embedding, whisper, TTS, and rerank models are automatically excluded.

```json
{
  "models": ["llama3.1:8b", "qwen2.5:14b"],
  "active": "llama3.1:8b"
}
```

### `GET /api/running`

Returns models currently loaded in Ollama memory with RAM and VRAM usage.

```json
{
  "models": [
    {
      "name": "llama3.1:8b",
      "size_gb": 4.7,
      "vram_gb": 4.7,
      "expires_at": "2024-01-01T00:05:00Z"
    }
  ]
}
```

### `POST /api/models/unload`

Evicts a model from memory immediately.

```json
{ "model": "llama3.1:8b" }
```

```json
{ "ok": true, "model": "llama3.1:8b", "action": "unloaded" }
```

### `POST /api/models/load`

Pre-loads a model into memory (keeps it warm for 10 minutes).

```json
{ "model": "llama3.1:8b" }
```

```json
{ "ok": true, "model": "llama3.1:8b", "action": "loaded" }
```

### `POST /api/generate`

Generate reply suggestions for a post.

**Request:**
```json
{
  "post": "The tweet or topic you want to reply to",
  "use_web": false,
  "model": "llama3.1:8b"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `post` | string | Yes | The tweet text (max 4000 chars) |
| `use_web` | boolean | No | Search DuckDuckGo for context before generating |
| `model` | string | No | Override the default model for this request |

**Response:**
```json
{
  "replies": [
    { "style": "professional", "text": "..." },
    { "style": "bold",         "text": "..." },
    { "style": "witty",        "text": "..." }
  ],
  "model": "llama3.1:8b",
  "web_sources": ["https://example.com/article"]
}
```

---

## Extending ReplyForge

The codebase is intentionally minimal. Here is where to plug in future features:

| Feature | Where to add it |
|---|---|
| **Streaming** (token-by-token) | Flip `"stream": True` in `call_ollama`, switch endpoint to `StreamingResponse` (SSE), update frontend fetch to use `ReadableStream` |
| **Memory / history** | Add `backend/memory.py`, store prior posts+replies in SQLite, inject top-k matches as a context block in `build_user_prompt` |
| **RAG** | Add a vector store (e.g. `sqlite-vss`), embed posts at generation time, retrieve similar past content as context |
| **Tool calling** | Ollama supports `tools` natively on Llama 3.1+. Pass tool schemas in the payload, loop on `tool_calls` in the response |
| **Twitter API posting** | Add a `POST /api/post` endpoint that calls X API v2 with an OAuth 2.0 token. Wire the "Post on X" button to it instead of the intent URL |
| **Analytics** | Add `backend/analytics.py`, append `(post_hash, style_picked, latency_ms, model)` to a SQLite table on each generate call |
| **Voice input** | Add Whisper.cpp via an Ollama-compatible endpoint for STT; pipe transcript into the composer |
| **Multi-agent** | Replace the single `call_ollama` with `asyncio.gather()` over three focused per-style prompts |

---

## Troubleshooting

**`Ollama is not reachable`**
Start Ollama: `ollama serve` or open the Ollama macOS/Windows app.

**`Model not installed`**
Pull the model shown in the error: `ollama pull llama3.1:8b`

**`Model did not return valid JSON`**
Some smaller models ignore the `format: "json"` instruction. Switch to a larger model (`qwen2.5:14b` is reliable).

**`Ollama timed out`**
Increase `OLLAMA_TIMEOUT` in `.env`, or switch to a smaller/faster model.

**`ReplyForge.command` blocked by macOS**
Right-click the file → **Open** → **Open** to bypass Gatekeeper permanently.

**Web context toggle is slow**
DuckDuckGo search adds ~2–4 seconds before inference begins. This is normal.

**Model Manager shows no models**
Ollama is not running or has no models installed. Run `ollama pull llama3.1:8b` first.

**Unload/Load buttons don't respond**
The backend must be running. Check the terminal where you ran `./run.sh` for errors.

---

## License

MIT — do whatever you want with it.

---

Built with FastAPI, Ollama, and zero cloud dependencies · Made by [@NayanUnfiltered](https://x.com/NayanUnfiltered)
