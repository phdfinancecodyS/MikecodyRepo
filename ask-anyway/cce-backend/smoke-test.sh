#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "[smoke] GET ${BASE_URL}/health"
health_json="$(curl -fsS "${BASE_URL}/health")"
echo "[smoke] health=${health_json}"

echo "[smoke] GET ${BASE_URL}/trees"
trees_json="$(curl -fsS "${BASE_URL}/trees")"
echo "${trees_json}" | grep -q '"main-flow"' || { echo "[smoke] main-flow tree missing"; exit 1; }

echo "[smoke] POST ${BASE_URL}/session/start"
start_json="$(curl -fsS -X POST "${BASE_URL}/session/start" -H 'Content-Type: application/json' -d '{"tree_id":"main-flow"}')"
echo "[smoke] start=${start_json}"

session_id="$(printf '%s' "${start_json}" | sed -n 's/.*"session_id":"\([^"]*\)".*/\1/p')"
if [ -z "${session_id}" ]; then
  echo "[smoke] failed to parse session_id"
  exit 1
fi

echo "[smoke] POST ${BASE_URL}/session/${session_id}/respond"
respond_json="$(curl -fsS -X POST "${BASE_URL}/session/${session_id}/respond" -H 'Content-Type: application/json' -d '{"message":"rough day"}')"
echo "[smoke] respond=${respond_json}"
echo "${respond_json}" | grep -q '"status":"in_progress"\|"status":"needs_clarification"\|"status":"complete"' || { echo "[smoke] unexpected respond status"; exit 1; }

echo "[smoke] PASS"
