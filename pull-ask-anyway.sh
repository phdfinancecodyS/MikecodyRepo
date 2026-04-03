#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="${ROOT_DIR}/ask-anyway"

if [ ! -d "${REPO_DIR}/.git" ]; then
  echo "[pull] Not a git repo: ${REPO_DIR}"
  exit 1
fi

cd "${REPO_DIR}"

if [ -n "$(git status --porcelain)" ]; then
  echo "[pull] Working tree is not clean in ${REPO_DIR}"
  echo "[pull] Commit or stash changes first, then run this again."
  git status --short
  exit 2
fi

branch="$(git branch --show-current)"
if [ -z "${branch}" ]; then
  echo "[pull] Could not detect current branch"
  exit 1
fi

echo "[pull] Fetching origin..."
git fetch origin

echo "[pull] Pulling latest on ${branch}..."
git pull --rebase origin "${branch}"

echo "[pull] Done"
