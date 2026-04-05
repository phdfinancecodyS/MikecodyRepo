#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
WEB_DIR="${ROOT_DIR}/web"
BACKEND_DIR="${ROOT_DIR}/ask-anyway/cce-backend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
CANONICAL_UI_URL="http://127.0.0.1:${FRONTEND_PORT}/ask-anyway-chat.html"
CCE_CORS_ORIGINS="${CCE_CORS_ORIGINS:-http://127.0.0.1:${FRONTEND_PORT}}"

if [ ! -d "${WEB_DIR}" ]; then
  echo "[root] Missing web app directory: ${WEB_DIR}"
  exit 1
fi

if [ ! -x "${BACKEND_DIR}/start.sh" ]; then
  echo "[root] Missing backend start script: ${BACKEND_DIR}/start.sh"
  exit 1
fi

if lsof -iTCP:"${BACKEND_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
    echo "[root] Backend port ${BACKEND_PORT} is already in use."
  else
    echo "[root] Backend port ${BACKEND_PORT} appears stale. Waiting for release..."
    for i in {1..10}; do
      if ! lsof -iTCP:"${BACKEND_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done
  fi
fi

if ! curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
  echo "[root] Starting backend on ${BACKEND_PORT}..."
  (
    cd "${BACKEND_DIR}"
    CCE_CORS_ORIGINS="${CCE_CORS_ORIGINS}" CCE_PORT="${BACKEND_PORT}" ./start.sh
  ) &
fi

if lsof -iTCP:"${FRONTEND_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[root] Frontend port ${FRONTEND_PORT} is already in use."
else
  echo "[root] Starting Next.js frontend on ${FRONTEND_PORT}..."
  (
    cd "${WEB_DIR}"
    npm run dev -- --hostname 127.0.0.1 --port "${FRONTEND_PORT}"
  ) >/tmp/ask-anyway-web.log 2>&1 &
fi

echo "[root] Waiting for backend health endpoint..."
for i in {1..30}; do
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null; then
    break
  fi
  sleep 1
done

echo "[root] Waiting for frontend endpoint..."
for i in {1..60}; do
  if curl -fsS "${CANONICAL_UI_URL}" >/dev/null; then
    break
  fi
  sleep 1
done

echo "[root] Canonical UI: ${CANONICAL_UI_URL}"
echo "[root] Backend docs: http://127.0.0.1:${BACKEND_PORT}/docs"
