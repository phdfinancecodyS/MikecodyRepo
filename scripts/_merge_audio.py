#!/usr/bin/env python3
"""
Merge voiceover audio onto the campaign video using ffmpeg directly.
Bypasses MoviePy's audio pipeline for maximum compatibility.
"""
import json
import os
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

ROOT = Path(__file__).resolve().parent.parent
ffmpeg = get_ffmpeg_exe()
vo_dir = ROOT / "output" / "videos" / "vo"
video_in = ROOT / "output" / "videos" / "ask-anyway-campaign-intro.mp4"
video_out = ROOT / "output" / "videos" / "ask-anyway-campaign-final.mp4"

# Load manifest for timing
manifest = json.loads((vo_dir / "manifest.json").read_text())

slide_durations = []
for i in range(1, 9):
    d = manifest[str(i)]["duration"] + 0.5
    slide_durations.append(d)

print("Slide durations:", [f"{d:.2f}" for d in slide_durations])
print("Total:", f"{sum(slide_durations):.2f}s")

# Build ffmpeg filter: delay each VO clip to its slide start time and boost volume
inputs = ["-i", str(video_in)]
filter_parts = []
for i in range(1, 9):
    vo_file = vo_dir / f"slide-{i:02d}.mp3"
    inputs.extend(["-i", str(vo_file)])
    delay_ms = int(sum(slide_durations[:i - 1]) * 1000)
    # Input index is i (0 is the video)
    filter_parts.append(f"[{i}]adelay={delay_ms}|{delay_ms},volume=5.0[a{i}]")

mix_inputs = "".join(f"[a{j}]" for j in range(1, 9))
filter_str = ";".join(filter_parts)
filter_str += f";{mix_inputs}amix=inputs=8:duration=longest:dropout_transition=0[aout]"

cmd = [
    ffmpeg, "-y",
    *inputs,
    "-filter_complex", filter_str,
    "-map", "0:v",
    "-map", "[aout]",
    "-c:v", "copy",
    "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
    "-shortest",
    str(video_out),
]

print("Running ffmpeg...")
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("FAILED!")
    print(result.stderr[-1000:])
else:
    size = os.path.getsize(video_out)
    print(f"Success! Output: {video_out}")
    print(f"Size: {size / 1024:.0f} KB")

# Open it
print("Opening video...")
subprocess.run(["open", str(video_out)])
