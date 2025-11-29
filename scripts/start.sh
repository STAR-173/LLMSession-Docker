#!/bin/bash
set -e

DISPLAY_PORT=":99"
SESSION_DIR="/root/.local/share/LLMSession"

echo "--- Starting LLM Session Service ---"

# 1. CLEANUP: Remove Chrome Singleton Locks from previous crashes
#    This fixes the "Profile appears to be in use" error.
if [ -d "$SESSION_DIR" ]; then
    echo "[Startup] Cleaning up stale Chrome locks..."
    rm -f "$SESSION_DIR/SingletonLock"
    rm -f "$SESSION_DIR/SingletonCookie"
    rm -f "$SESSION_DIR/SingletonSocket"
fi

# 2. Start Xvfb (Virtual Framebuffer)
echo "[Startup] Launching Xvfb on $DISPLAY_PORT..."
Xvfb $DISPLAY_PORT -ac -screen 0 1280x1024x24 &

# 3. Export DISPLAY
export DISPLAY=$DISPLAY_PORT

echo "[Startup] Waiting for Xvfb..."
sleep 2

# 4. Start VNC Server (Optional, for debugging)
echo "[Startup] Launching VNC Server..."
x11vnc -display $DISPLAY_PORT -forever -nopw -quiet -listen 0.0.0.0 -xkb &

# 5. Start FastAPI
echo "[Startup] Launching Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
