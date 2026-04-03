#!/usr/bin/env python3
"""
Generate voiceover clips using ElevenLabs API.
Supports audition mode (test one line with multiple voices)
and full render mode (all 3 slides with chosen voice).

Usage:
  python build_voiceover_elevenlabs.py audition   # test voices
  python build_voiceover_elevenlabs.py render      # full production VO
  python build_voiceover_elevenlabs.py render VOICE_ID  # specific voice
"""
import json
import os
import sys
from pathlib import Path

from elevenlabs import ElevenLabs

ROOT = Path(__file__).resolve().parent.parent
VO_DIR = ROOT / "output" / "videos" / "vo2"
VO_DIR.mkdir(parents=True, exist_ok=True)
AUDITION_DIR = ROOT / "output" / "videos" / "vo_audition"
AUDITION_DIR.mkdir(parents=True, exist_ok=True)

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# Voice candidates for audition
VOICE_CANDIDATES = {
    "sarah": "EXAVITQu4vr4xnSDxMaL",   # Mature, Reassuring, Confident
    "jessica": "cgSgspJ2msm6clMCkdW9",  # Playful, Bright, Warm
    "bella": "hpp4J3VqNfWAUOO0d1Us",    # Professional, Bright, Warm
}

# Default production voice (set after audition)
DEFAULT_VOICE = "jessica"

# VO script — 3 slides for stick figure animation
SLIDES = [
    {
        "num": 1,
        "text": "Someone you love is struggling, and you have no idea what to say.",
    },
    {
        "num": 2,
        "text": "You're not scared of saying the wrong thing. You're scared of saying nothing at all.",
    },
    {
        "num": 3,
        "text": "So you just... don't bring it up. And that silence? It stays with you.",
    },
]

MODEL = "eleven_multilingual_v2"


def get_duration(path):
    """Get audio duration in seconds."""
    from moviepy import AudioFileClip
    ac = AudioFileClip(str(path))
    dur = ac.duration
    ac.close()
    return dur


def audition():
    """Generate one test line with each candidate voice for comparison."""
    client = ElevenLabs(api_key=API_KEY)
    test_text = SLIDES[0]["text"]

    print(f"Audition line: \"{test_text}\"\n")

    for name, voice_id in VOICE_CANDIDATES.items():
        out_path = AUDITION_DIR / f"audition-{name}.mp3"
        print(f"  Generating {name}...", end=" ", flush=True)

        audio = client.text_to_speech.convert(
            text=test_text,
            voice_id=voice_id,
            model_id=MODEL,
            output_format="mp3_44100_128",
        )

        with open(out_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)

        dur = get_duration(out_path)
        print(f"{dur:.2f}s -> {out_path.name}")

    print(f"\nAudition clips saved to: {AUDITION_DIR}")
    print("Listen and pick your favorite, then run:")
    print("  python build_voiceover_elevenlabs.py render <voice_name>")
    print(f"  (options: {', '.join(VOICE_CANDIDATES.keys())})")

    # Open the folder
    import subprocess
    subprocess.run(["open", str(AUDITION_DIR)])


def render(voice_name=None):
    """Generate all 3 VO slides with the chosen voice."""
    if voice_name is None:
        voice_name = DEFAULT_VOICE

    if voice_name not in VOICE_CANDIDATES:
        print(f"Unknown voice '{voice_name}'. Options: {', '.join(VOICE_CANDIDATES.keys())}")
        sys.exit(1)

    voice_id = VOICE_CANDIDATES[voice_name]
    client = ElevenLabs(api_key=API_KEY)

    print(f"Rendering VO with voice: {voice_name} ({voice_id[:12]}...)")
    print(f"Model: {MODEL}\n")

    manifest = {}
    for slide in SLIDES:
        out_path = VO_DIR / f"slide-{slide['num']:02d}.mp3"
        print(f"  Slide {slide['num']}: \"{slide['text'][:50]}...\"", end=" ", flush=True)

        audio = client.text_to_speech.convert(
            text=slide["text"],
            voice_id=voice_id,
            model_id=MODEL,
            output_format="mp3_44100_128",
        )

        with open(out_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)

        dur = get_duration(out_path)
        print(f"-> {dur:.2f}s")

        manifest[str(slide["num"])] = {
            "file": f"slide-{slide['num']:02d}.mp3",
            "text": slide["text"],
            "duration": round(dur, 2),
        }

    (VO_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    total = sum(v["duration"] for v in manifest.values())
    print(f"\nTotal VO: {total:.1f}s")
    print(f"Manifest: {VO_DIR / 'manifest.json'}")
    print(f"Voice: {voice_name}")
    print("\nNow rebuild video: python build_campaign_video_v3.py")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python build_voiceover_elevenlabs.py audition")
        print("  python build_voiceover_elevenlabs.py render [voice_name]")
        sys.exit(1)

    mode = sys.argv[1].lower()
    if mode == "audition":
        audition()
    elif mode == "render":
        voice = sys.argv[2].lower() if len(sys.argv) > 2 else None
        render(voice)
    else:
        print(f"Unknown mode: {mode}. Use 'audition' or 'render'.")
