from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import settings
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .web import fetch_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("replyforge")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

Style = Literal["professional", "bold", "witty"]


class GenerateRequest(BaseModel):
    post: str = Field(..., min_length=1, max_length=4000)
    use_web: bool = False
    model: str | None = None  # overrides settings.model for this request


class Reply(BaseModel):
    style: str
    text: str


class GenerateResponse(BaseModel):
    replies: list[Reply]
    model: str
    web_sources: list[str] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    timeout = httpx.Timeout(settings.ollama_timeout, connect=5.0)
    app.state.http = httpx.AsyncClient(timeout=timeout)
    log.info("ReplyForge ready. Ollama=%s model=%s", settings.ollama_host, settings.model)
    try:
        yield
    finally:
        await app.state.http.aclose()


app = FastAPI(title="ReplyForge", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Ollama transport ---------------------------------------------------

async def call_ollama(
    client: httpx.AsyncClient,
    post: str,
    model: str,
    web_context: str = "",
) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(post, web_context)},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "num_predict": 700,
        },
    }

    try:
        r = await client.post(f"{settings.ollama_host}/api/chat", json=payload)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Ollama is not reachable. Start it with `ollama serve` (or open the Ollama app).",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Ollama timed out. Try a smaller model or increase OLLAMA_TIMEOUT in .env.",
        )

    if r.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"Model `{model}` not installed. Run: ollama pull {model}",
        )
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Ollama error {r.status_code}: {r.text[:300]}")

    data = r.json()
    content = (data.get("message") or {}).get("content", "")
    if not content:
        raise HTTPException(status_code=502, detail="Empty response from model.")
    return content


# ---------- Parsing ------------------------------------------------------------

def _truncate_280(text: str) -> str:
    text = text.strip().strip("\"'`")
    if len(text) <= 280:
        return text
    cut = text[:279].rsplit(" ", 1)[0]
    return (cut.rstrip(",.;:!?-") + "…")[:280]


def parse_replies(raw: str) -> list[Reply]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            raise HTTPException(502, "Model did not return valid JSON. Try regenerating.")
        try:
            data = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            raise HTTPException(502, "Model did not return valid JSON. Try regenerating.")

    items = data.get("replies") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise HTTPException(502, "Model response missing `replies` array.")

    out: list[Reply] = []
    for item in items[:3]:
        if not isinstance(item, dict):
            continue
        text = (item.get("text") or "").strip()
        style = (item.get("style") or "general").strip().lower()
        if not text:
            continue
        out.append(Reply(style=style, text=_truncate_280(text)))

    if not out:
        raise HTTPException(502, "Model returned no usable replies. Try again.")
    return out


# ---------- API ----------------------------------------------------------------

@app.get("/api/health")
async def health():
    try:
        r = await app.state.http.get(f"{settings.ollama_host}/api/tags", timeout=3.0)
        if r.status_code != 200:
            return {"status": "degraded", "ollama": "unreachable", "model": settings.model}
        installed = [m.get("name", "") for m in r.json().get("models", [])]
        present = any(name == settings.model or name.startswith(settings.model + ":") for name in installed)
        return {
            "status": "ok",
            "ollama": "running",
            "model": settings.model,
            "model_installed": present,
            "installed_models": installed,
        }
    except (httpx.ConnectError, httpx.TimeoutException):
        return {"status": "degraded", "ollama": "not running", "model": settings.model}


_EXCLUDED_FAMILIES = ("vision", "embed", "whisper", "tts", "clip", "rerank")


def _is_text_model(name: str) -> bool:
    lower = name.lower()
    return not any(tag in lower for tag in _EXCLUDED_FAMILIES)


@app.get("/api/models")
async def list_models():
    """Return locally installed Ollama text-generation models (excludes vision/embed/etc.)."""
    try:
        r = await app.state.http.get(f"{settings.ollama_host}/api/tags", timeout=3.0)
        if r.status_code != 200:
            return {"models": []}
        all_models = [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
        models = [m for m in all_models if _is_text_model(m)]
        return {"models": models, "active": settings.model}
    except (httpx.ConnectError, httpx.TimeoutException):
        return {"models": [], "active": settings.model}


@app.get("/api/running")
async def running_models():
    """Return models currently loaded in Ollama memory with size info."""
    try:
        r = await app.state.http.get(f"{settings.ollama_host}/api/ps", timeout=3.0)
        if r.status_code != 200:
            return {"models": []}
        models = []
        for m in r.json().get("models", []):
            name = m.get("name") or m.get("model", "")
            if not name:
                continue
            size_bytes = m.get("size", 0)
            size_vram  = m.get("size_vram", 0)
            models.append({
                "name":       name,
                "size_gb":    round(size_bytes / 1e9, 1) if size_bytes else None,
                "vram_gb":    round(size_vram  / 1e9, 1) if size_vram  else None,
                "expires_at": m.get("expires_at"),
            })
        return {"models": models}
    except (httpx.ConnectError, httpx.TimeoutException):
        return {"models": []}


class ModelActionRequest(BaseModel):
    model: str = Field(..., min_length=1)


@app.post("/api/models/unload")
async def unload_model(req: ModelActionRequest):
    """Evict a model from Ollama memory by setting keep_alive to 0."""
    try:
        r = await app.state.http.post(
            f"{settings.ollama_host}/api/generate",
            json={"model": req.model, "keep_alive": 0},
            timeout=10.0,
        )
        if r.status_code >= 400:
            raise HTTPException(502, f"Ollama error: {r.text[:200]}")
        return {"ok": True, "model": req.model, "action": "unloaded"}
    except httpx.ConnectError:
        raise HTTPException(503, "Ollama is not reachable.")
    except httpx.TimeoutException:
        raise HTTPException(504, "Request timed out.")


@app.post("/api/models/load")
async def load_model(req: ModelActionRequest):
    """Pre-load a model into Ollama memory (keep_alive = 10 minutes)."""
    try:
        r = await app.state.http.post(
            f"{settings.ollama_host}/api/generate",
            json={"model": req.model, "keep_alive": "10m", "prompt": ""},
            timeout=120.0,
        )
        if r.status_code == 404:
            raise HTTPException(404, f"Model `{req.model}` is not installed. Run: ollama pull {req.model}")
        if r.status_code >= 400:
            raise HTTPException(502, f"Ollama error: {r.text[:200]}")
        return {"ok": True, "model": req.model, "action": "loaded"}
    except httpx.ConnectError:
        raise HTTPException(503, "Ollama is not reachable.")
    except httpx.TimeoutException:
        raise HTTPException(504, "Model load timed out — it may still be loading in the background.")


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    post = req.post.strip()
    if not post:
        raise HTTPException(400, "Post cannot be empty.")

    model = req.model or settings.model
    web_context = ""
    sources: list[str] = []

    if req.use_web:
        log.info("generate: fetching web context for post (len=%d)", len(post))
        # Use first 120 chars of the post as the search query
        query = post[:120].strip()
        web_context, sources = await fetch_context(query)
        log.info("generate: got %d web sources", len(sources))

    log.info("generate: model=%s web=%s len=%d", model, req.use_web, len(post))
    raw = await call_ollama(app.state.http, post, model, web_context)
    replies = parse_replies(raw)
    return GenerateResponse(replies=replies, model=model, web_sources=sources)


# ---------- Static frontend ----------------------------------------------------

app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR)), name="assets")


@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
