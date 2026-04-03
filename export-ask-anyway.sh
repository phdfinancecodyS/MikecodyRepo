#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: ./export-ask-anyway.sh \"commit message\""
  exit 1
fi

MESSAGE="$1"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="${ROOT_DIR}/ask-anyway"

if [ ! -d "${REPO_DIR}/.git" ]; then
  echo "[export] Not a git repo: ${REPO_DIR}"
  exit 1
fi

cd "${REPO_DIR}"

branch="$(git branch --show-current)"
if [ -z "${branch}" ]; then
  echo "[export] Could not detect current branch"
  exit 1
fi

if [ -z "$(git status --porcelain)" ]; then
  echo "[export] No local changes to commit"
  exit 0
fi

echo "[export] Staging changes..."
git add -A

echo "[export] Committing..."
git commit -m "${MESSAGE}"

echo "[export] Pushing to origin/${branch}..."
git push origin "${branch}"

echo "[export] Done"
