#!/usr/bin/env bash
# ─── CCE Start Script ───────────────────────────────────────────────────────
# Activates (or creates) a venv, installs deps if needed, starts the server.
set -e
cd "$(dirname "$0")"

VENV=".venv"

if [ ! -d "$VENV" ]; then
  echo "[cce] Creating virtual environment..."
  python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"

echo "[cce] Installing / verifying dependencies..."
pip install -r requirements.txt -q

export CCE_CORS_ORIGINS="${CCE_CORS_ORIGINS:-http://localhost:3131}"
export CCE_PORT="${CCE_PORT:-8000}"
export CCE_LOG_LEVEL="${CCE_LOG_LEVEL:-info}"

echo "[cce] Starting CCE API on port $CCE_PORT (CORS: $CCE_CORS_ORIGINS)"
python3 launcher.py
