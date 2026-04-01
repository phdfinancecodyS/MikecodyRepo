#!/bin/zsh
# push-anyway.sh — Stage, commit, and push everything with a message
# Usage: bash push-anyway.sh "what you changed"
# Example: bash push-anyway.sh "updated hedging detection"

REPO_DIR="/Users/codysullivan/Documents"
BRANCH="main"
WHO="Cody"

cd "$REPO_DIR" || exit 1

MSG="${1:-update}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')

# Write a ping file so the other side's watcher sees a human-readable note
echo "Push from $WHO — $TIMESTAMP — $MSG" > SYNC_PING.txt

git add -A
git commit -m "$MSG" --quiet

if git push origin "$BRANCH" --quiet; then
  echo "✓ Pushed: \"$MSG\""
  echo "  Mike's watcher will auto-pull in ≤30 seconds."
else
  echo "✗ Push failed — check your connection or auth."
  exit 1
fi
