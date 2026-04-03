#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SMOKE_SCRIPT="${ROOT_DIR}/ask-anyway/cce-backend/smoke-test.sh"

if [ ! -x "${SMOKE_SCRIPT}" ]; then
  echo "[root] Missing executable script: ${SMOKE_SCRIPT}"
  echo "[root] Run setup first: ./run-ask-anyway-shared.sh"
  exit 1
fi

exec "${SMOKE_SCRIPT}"
