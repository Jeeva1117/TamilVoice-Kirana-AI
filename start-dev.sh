#!/usr/bin/env bash
# TamilVoice Kirana AI - Development Launcher for Linux / macOS
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

PYTHON_CMD="python3"
if [ -d "venv" ]; then
    PYTHON_CMD="./venv/bin/python"
elif [ -d ".venv" ]; then
    PYTHON_CMD="./.venv/bin/python"
fi

echo "========================================================================"
echo "       TamilVoice Kirana AI - Local Development Environment"
echo "========================================================================"
echo "[*] Using Python: $($PYTHON_CMD --version)"
echo "[*] Starting FastAPI Backend on http://127.0.0.1:8000 ..."
$PYTHON_CMD -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

echo "[*] Starting Frontend Web Server on http://127.0.0.1:3000 ..."
$PYTHON_CMD -m http.server 3000 --directory frontend &
FRONTEND_PID=$!

cleanup() {
    echo ""
    echo "[*] Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

echo ""
echo "========================================================================"
echo "  TamilVoice Kirana AI is now running!"
echo "  Frontend App:     http://127.0.0.1:3000"
echo "  FastAPI Root:     http://127.0.0.1:8000"
echo "  Interactive Docs: http://127.0.0.1:8000/docs"
echo "  Health Status:    http://127.0.0.1:8000/health"
echo "  Press Ctrl+C to stop both servers."
echo "========================================================================"
wait

