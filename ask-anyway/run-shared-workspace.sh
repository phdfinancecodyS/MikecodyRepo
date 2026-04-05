#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CANONICAL_RUNNER="${ROOT_DIR}/../run-ask-anyway-shared.sh"

if [ ! -x "${CANONICAL_RUNNER}" ]; then
  echo "[shared] Missing canonical runner: ${CANONICAL_RUNNER}"
  exit 1
fi

echo "[shared] Delegating to canonical runner at repo root."
exec "${CANONICAL_RUNNER}"
