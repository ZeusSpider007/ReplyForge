#!/usr/bin/env bash
# Double-click this file to launch ReplyForge.
set -eo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Load .env first so PORT/HOST from it take effect
if [ -f "$DIR/.env" ]; then
  while IFS='=' read -r key value; do
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    export "$key"="${value}"
  done < "$DIR/.env"
fi

PORT="${PORT:-8000}"
URL="http://127.0.0.1:${PORT}"

echo ""
echo "  🔥 ReplyForge"
echo "  ─────────────────────────────"

# ── 1. Start Ollama if not already running ─────────────────────────────────
if curl -sf "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
  echo "  ✓ Ollama already running"
else
  echo "  ↗ Starting Ollama…"
  ollama serve &>/tmp/replyforge-ollama.log &
  OLLAMA_PID=$!

  for i in $(seq 1 15); do
    sleep 1
    if curl -sf "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
      echo "  ✓ Ollama started"
      break
    fi
    if [ "$i" -eq 15 ]; then
      echo "  ✗ Ollama failed to start. Check /tmp/replyforge-ollama.log"
      exit 1
    fi
  done
fi

# ── 2. Activate venv ───────────────────────────────────────────────────────
if [ -f "$DIR/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$DIR/.venv/bin/activate"
else
  echo "  ✗ Virtual environment not found."
  echo "    Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# ── 3. Start ReplyForge backend ────────────────────────────────────────────
echo "  ↗ Starting ReplyForge on $URL…"
uvicorn backend.main:app --host 127.0.0.1 --port "$PORT" &>/tmp/replyforge-server.log &
SERVER_PID=$!

# ── 4. Wait for server to be ready ────────────────────────────────────────
for i in $(seq 1 20); do
  sleep 0.5
  if curl -sf "$URL/api/health" >/dev/null 2>&1; then
    echo "  ✓ ReplyForge is ready"
    break
  fi
  if [ "$i" -eq 20 ]; then
    echo "  ✗ Server failed to start. Check /tmp/replyforge-server.log"
    kill "$SERVER_PID" 2>/dev/null || true
    exit 1
  fi
done

# ── 5. Open browser ───────────────────────────────────────────────────────
echo "  ✓ Opening $URL"
echo ""
open "$URL"

# ── 6. Keep terminal open; kill server on Ctrl-C ──────────────────────────
echo "  Press Ctrl-C to stop ReplyForge."
echo ""
trap 'echo ""; echo "  Stopping ReplyForge…"; kill "$SERVER_PID" 2>/dev/null; exit 0' INT TERM

wait "$SERVER_PID"
