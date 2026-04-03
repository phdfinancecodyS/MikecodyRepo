#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

python scripts/_gen_ambient.py

if [[ -n "${ELEVENLABS_API_KEY:-}" ]]; then
  python scripts/build_voiceover_elevenlabs.py render jessica
else
  echo "ELEVENLABS_API_KEY not set. Using existing VO files in output/videos/vo2/."
fi

python scripts/build_campaign_video_v3.py

echo "Build complete. Check output/videos/ask-anyway-v3.mp4"
