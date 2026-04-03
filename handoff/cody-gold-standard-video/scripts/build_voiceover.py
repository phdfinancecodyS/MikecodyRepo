#!/usr/bin/env python3
"""
Generate per-slide voiceover audio for the campaign intro video using Edge TTS.

Each slide gets its own audio file with natural pacing. The main video builder
then syncs slide durations to the voiceover length.

Usage:
    python3 scripts/build_voiceover.py

Output:
    output/videos/vo/slide-01.mp3
    output/videos/vo/slide-02.mp3
    ...
    output/videos/vo/slide-08.mp3
"""

import asyncio
import json
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent.parent
VO_DIR = ROOT / "output" / "videos" / "vo"
VO_DIR.mkdir(parents=True, exist_ok=True)

# Warm, natural female voice
VOICE = "en-US-AvaNeural"

# Voiceover script - one entry per slide
# Each line is spoken with a brief pause between slides
SLIDES = [
    {
        "id": 1,
        "text": "You don't need training to save someone's life.",
        "rate": "-5%",
        "pitch": "+0Hz",
    },
    {
        "id": 2,
        "text": "You just need the courage to ask.",
        "rate": "-8%",
        "pitch": "+0Hz",
    },
    {
        "id": 3,
        "text": "Most people don't ask, because they're afraid of saying the wrong thing.",
        "rate": "-5%",
        "pitch": "+0Hz",
    },
    {
        "id": 4,
        "text": "But silence is scarier than the wrong words.",
        "rate": "-10%",
        "pitch": "+0Hz",
    },
    {
        "id": 5,
        "text": "So we built a guide for people who care enough to ask anyway.",
        "rate": "-5%",
        "pitch": "+0Hz",
    },
    {
        "id": 6,
        "text": "How to start the conversation. How to stay in it when it gets hard. And what to do next.",
        "rate": "-8%",
        "pitch": "+0Hz",
    },
    {
        "id": 7,
        "text": "Created by a licensed clinical social worker and loss survivor. Real talk. No jargon. Just what actually helps.",
        "rate": "-5%",
        "pitch": "+0Hz",
    },
    {
        "id": 8,
        "text": "Take the free quiz. Link in bio.",
        "rate": "-10%",
        "pitch": "+0Hz",
    },
]


async def generate_slide_audio(slide):
    """Generate audio for a single slide."""
    output_path = VO_DIR / f"slide-{slide['id']:02d}.mp3"
    communicate = edge_tts.Communicate(
        slide["text"],
        VOICE,
        rate=slide.get("rate", "+0%"),
        pitch=slide.get("pitch", "+0Hz"),
    )
    await communicate.save(str(output_path))
    return output_path


async def main():
    print(f"Generating voiceover with voice: {VOICE}")
    print(f"Output: {VO_DIR}\n")

    durations = {}

    for slide in SLIDES:
        path = await generate_slide_audio(slide)

        # Get duration using moviepy
        from moviepy import AudioFileClip
        clip = AudioFileClip(str(path))
        dur = clip.duration
        clip.close()

        durations[slide["id"]] = {
            "file": str(path),
            "duration": round(dur, 2),
            "text": slide["text"],
        }
        print(f"  Slide {slide['id']}: {dur:.2f}s - \"{slide['text'][:50]}...\"")

    # Save duration manifest for the video builder
    manifest_path = VO_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(durations, indent=2))

    total = sum(d["duration"] for d in durations.values())
    print(f"\nTotal voiceover: {total:.1f}s")
    print(f"Manifest saved: {manifest_path}")


if __name__ == "__main__":
    asyncio.run(main())
