#!/bin/bash
set -e

DISPLAY_PORT=":99"
SESSION_DIR="/root/.local/share/LLMSession"

echo "--- Starting LLM Session Service (Production) ---"

# 1. CLEANUP: Remove Chrome Singleton Locks
# Prevents crash loops if the container was killed abruptly
if [ -d "$SESSION_DIR" ]; then
    echo "[Startup] Cleaning up stale Chrome locks..."
    find "$SESSION_DIR" -name "SingletonLock" -delete
    find "$SESSION_DIR" -name "SingletonCookie" -delete
    find "$SESSION_DIR" -name "SingletonSocket" -delete
fi

# 2. Start Xvfb
# Required because the providers run with headless=False to avoid detection
echo "[Startup] Launching Xvfb on $DISPLAY_PORT..."
Xvfb $DISPLAY_PORT -ac -screen 0 1280x1024x24 &

# 3. Export DISPLAY
export DISPLAY=$DISPLAY_PORT

echo "[Startup] Waiting for Xvfb..."
sleep 2

# 4. Start FastAPI
echo "[Startup] Launching Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000