#!/usr/bin/env bash
set -euo pipefail

FRONTEND_PORT="${FRONTEND_PORT:-3000}"
CANONICAL_UI_URL="http://127.0.0.1:${FRONTEND_PORT}/ask-anyway-chat.html"

echo "[open] Opening canonical UI only: ${CANONICAL_UI_URL}"
open "${CANONICAL_UI_URL}"
