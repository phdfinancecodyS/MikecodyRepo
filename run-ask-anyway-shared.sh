#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
INNER_SCRIPT="${ROOT_DIR}/ask-anyway/run-shared-workspace.sh"

if [ ! -x "${INNER_SCRIPT}" ]; then
  echo "[root] Missing executable script: ${INNER_SCRIPT}"
  echo "[root] Expected repo path: ${ROOT_DIR}/ask-anyway"
  exit 1
fi

exec "${INNER_SCRIPT}"
