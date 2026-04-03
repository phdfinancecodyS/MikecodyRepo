#!/usr/bin/env python3
"""
Merge v2 voiceover + ambient music bed onto the silent v2 video using ffmpeg.
"""
import json
import os
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

ROOT = Path(__file__).resolve().parent.parent
ffmpeg = get_ffmpeg_exe()

video_in = ROOT / "output" / "videos" / "v2_silent.mp4"
ambient = ROOT / "output" / "videos" / "ambient_pad.wav"
vo_dir = ROOT / "output" / "videos" / "vo2"
video_out = ROOT / "output" / "videos" / "ask-anyway-v2.mp4"

manifest = json.loads((vo_dir / "manifest.json").read_text())

# Calculate slide durations (VO duration + padding, matching build_campaign_video_v2.py)
pads = [0.5, 0.3, 0.3, 0.3, 0.5, 1.0]
slide_durations = []
for i in range(1, 7):
    d = manifest[str(i)]["duration"] + pads[i - 1]
    slide_durations.append(d)

print("Slide durations:", [f"{d:.2f}" for d in slide_durations])
print(f"Total: {sum(slide_durations):.2f}s")

# Build ffmpeg filter:
# - Input 0: video
# - Input 1: ambient pad
# - Inputs 2-7: VO clips (slides 1-6)
inputs = ["-i", str(video_in), "-i", str(ambient)]
filter_parts = []

# Ambient: trim to video length, set volume low
filter_parts.append("[1]atrim=0:22,asetpts=PTS-STARTPTS,volume=0.4[amb]")

# VO clips with delay and volume boost
for i in range(1, 7):
    vo_file = vo_dir / f"slide-{i:02d}.mp3"
    inputs.extend(["-i", str(vo_file)])
    delay_ms = int(sum(slide_durations[:i - 1]) * 1000)
    input_idx = i + 1  # 0=video, 1=ambient, 2+=VO
    filter_parts.append(
        f"[{input_idx}]adelay={delay_ms}|{delay_ms},volume=5.0[v{i}]"
    )

# Mix: ambient + all 6 VO clips
vo_labels = "".join(f"[v{j}]" for j in range(1, 7))
filter_parts.append(
    f"[amb]{vo_labels}amix=inputs=7:duration=shortest:dropout_transition=0,volume=1.5[aout]"
)

filter_str = ";".join(filter_parts)

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
    print(result.stderr[-1200:])
else:
    size = os.path.getsize(video_out)
    print(f"Success! {video_out}")
    print(f"Size: {size / 1024:.0f} KB")
    subprocess.run(["open", str(video_out)])
