#!/usr/bin/env bash
set -euo pipefail

# Stop servers commonly used for Ask Anyway local runs.
stop_port() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN || true)"
  if [ -n "${pids}" ]; then
    echo "[root] Stopping port ${port}: ${pids}"
    kill ${pids}
  else
    echo "[root] No listener on port ${port}"
  fi
}

stop_port 3131
stop_port 8000
stop_port 8787

echo "[root] Done"
