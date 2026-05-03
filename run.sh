#!/usr/bin/env bash
# ReplyForge launcher — verifies Ollama is up, then starts the API + UI.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[run.sh] Created .env from .env.example"
fi

# Load env without exporting unrelated vars
set -a
# shellcheck disable=SC1091
source .env
set +a

OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

if ! curl -sf "$OLLAMA_HOST/api/tags" >/dev/null 2>&1; then
  echo "[run.sh] Ollama is not running at $OLLAMA_HOST."
  echo "         Start it in another terminal:  ollama serve"
  echo "         (or open the Ollama macOS app)"
  exit 1
fi

if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

exec uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
