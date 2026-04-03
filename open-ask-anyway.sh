#!/usr/bin/env bash
set -euo pipefail

FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3131/ask-anyway-deploy/index.html}"
BACKEND_DOCS_URL="${BACKEND_DOCS_URL:-http://127.0.0.1:8000/docs}"

echo "[open] Opening frontend: ${FRONTEND_URL}"
open "${FRONTEND_URL}"

echo "[open] Opening backend docs: ${BACKEND_DOCS_URL}"
open "${BACKEND_DOCS_URL}"
