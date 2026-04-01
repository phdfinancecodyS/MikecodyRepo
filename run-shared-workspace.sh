#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3131}"
CCE_CORS_ORIGINS="${CCE_CORS_ORIGINS:-http://localhost:${FRONTEND_PORT}}"

if lsof -iTCP:"${BACKEND_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[shared] Backend port ${BACKEND_PORT} is already in use."
else
  echo "[shared] Starting backend on ${BACKEND_PORT}..."
  (
    cd "${ROOT_DIR}/cce-backend"
    CCE_CORS_ORIGINS="${CCE_CORS_ORIGINS}" CCE_PORT="${BACKEND_PORT}" ./start.sh
  ) &
fi

if lsof -iTCP:"${FRONTEND_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[shared] Frontend port ${FRONTEND_PORT} is already in use."
else
  echo "[shared] Starting static server on ${FRONTEND_PORT}..."
  python3 -m http.server "${FRONTEND_PORT}" --directory "${ROOT_DIR}" >/tmp/ask-anyway-frontend.log 2>&1 &
fi

echo "[shared] Waiting for backend health endpoint..."
for i in {1..30}; do
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null; then
    break
  fi
  sleep 1
done

echo "[shared] Frontend: http://127.0.0.1:${FRONTEND_PORT}/ask-anyway-deploy/index.html"
echo "[shared] Backend docs: http://127.0.0.1:${BACKEND_PORT}/docs"
echo "[shared] Run smoke test: ./cce-backend/smoke-test.sh"
