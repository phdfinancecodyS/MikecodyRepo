#!/usr/bin/env python3
"""
Generate v2 voiceover clips  - punchy, short, TikTok-paced.
"""
import asyncio
import json
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent.parent
VO_DIR = ROOT / "output" / "videos" / "vo2"
VO_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "en-US-MichelleNeural"

# New script: 6 slides, punchy, ~20s total
SLIDES = [
    {"num": 1, "text": "Someone you love is struggling, and you have no idea what to say.", "rate": "+12%"},
    {"num": 2, "text": "You're not scared of saying the wrong thing. You're scared of saying nothing at all.", "rate": "+10%"},
    {"num": 3, "text": "So you just... don't bring it up. And that silence? It stays with you.", "rate": "+10%"},
]


async def generate():
    manifest = {}
    for slide in SLIDES:
        out_path = VO_DIR / f"slide-{slide['num']:02d}.mp3"
        communicate = edge_tts.Communicate(
            slide["text"], VOICE, rate=slide["rate"]
        )
        await communicate.save(str(out_path))

        # Get duration
        from moviepy import AudioFileClip
        ac = AudioFileClip(str(out_path))
        dur = ac.duration
        ac.close()

        manifest[str(slide["num"])] = {
            "file": f"slide-{slide['num']:02d}.mp3",
            "text": slide["text"],
            "duration": round(dur, 2),
        }
        print(f"  Slide {slide['num']}: {dur:.2f}s - {slide['text'][:50]}")

    (VO_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    total = sum(v["duration"] for v in manifest.values())
    print(f"\nTotal VO: {total:.1f}s")


if __name__ == "__main__":
    asyncio.run(generate())
