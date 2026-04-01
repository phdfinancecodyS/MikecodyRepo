#!/bin/zsh
# watch-repo.sh — Auto-pull and notify when someone pushes to the repo
# Run once in a terminal tab: bash watch-repo.sh
# Leave it running — it checks every 30 seconds.

REPO_DIR="/Users/codysullivan/Documents"
BRANCH="main"
INTERVAL=30
WHO="Cody"   # your name — shows in the notification

cd "$REPO_DIR" || exit 1

echo "👁  Watching repo for changes every ${INTERVAL}s — $(date '+%H:%M:%S')"
echo "   Press Ctrl+C to stop."
echo ""

while true; do
  # Fetch silently
  git fetch origin "$BRANCH" --quiet 2>/dev/null

  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse "origin/$BRANCH")

  if [ "$LOCAL" != "$REMOTE" ]; then
    # Figure out what changed
    COMMITS=$(git log --oneline "$LOCAL".."$REMOTE")
    COUNT=$(echo "$COMMITS" | wc -l | tr -d ' ')
    FIRST_MSG=$(echo "$COMMITS" | head -1 | cut -d' ' -f2-)
    AUTHOR=$(git log -1 "origin/$BRANCH" --format="%an")

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔔  New push detected from $AUTHOR  ($(date '+%H:%M:%S'))"
    echo "    $COUNT commit(s):"
    echo "$COMMITS" | while read -r line; do
      echo "    • $line"
    done
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # macOS notification
    osascript -e "display notification \"$COUNT new commit(s) from $AUTHOR: $FIRST_MSG\" with title \"Ask Anyway Repo\" sound name \"Glass\""

    # Auto-pull (stash local uncommitted changes first so pull never fails)
    STASHED=false
    if ! git diff --quiet || ! git diff --cached --quiet; then
      git stash push -m "auto-stash before pull $(date +%s)" --quiet
      STASHED=true
    fi

    git pull origin "$BRANCH" --quiet

    if [ "$STASHED" = true ]; then
      git stash pop --quiet 2>/dev/null
      echo "    (local uncommitted changes were stashed and re-applied)"
    fi

    echo "    ✓ Auto-pulled. Repo is up to date."
    echo ""
  fi

  sleep "$INTERVAL"
done
