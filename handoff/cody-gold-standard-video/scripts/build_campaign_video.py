#!/usr/bin/env python3
"""
Generate a branded TikTok campaign introduction video for Ask Anyway.

Creates a text-reveal style vertical video (1080x1920) with branded colors,
fonts, and transitions. Uses Pillow for frame rendering and MoviePy for
video composition.

Usage:
    python3 scripts/build_campaign_video.py

Output:
    output/videos/ask-anyway-campaign-intro.mp4
"""

import os
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    concatenate_audioclips,
    ColorClip,
)

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "assets" / "fonts"
OUTPUT_DIR = ROOT / "output" / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Brand colors
TEAL = (26, 107, 106)        # #1a6b6a
AMBER = (212, 146, 42)       # #d4922a
WARM_WHITE = (250, 247, 242) # #faf7f2
CHARCOAL = (45, 45, 45)      # #2d2d2d
TEAL_DARK = (15, 78, 77)     # #0f4e4d

# Video dimensions (TikTok vertical)
W, H = 1080, 1920
FPS = 30

# Font paths
FONT_BLACK = str(FONTS_DIR / "Montserrat-Black.ttf")
FONT_BOLD = str(FONTS_DIR / "Montserrat-Bold.ttf")
FONT_REG = str(FONTS_DIR / "Montserrat-Regular.ttf")


def load_font(path, size):
    """Load a font, falling back to default if file missing."""
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        print(f"  Warning: Font not found: {path}, using default")
        return ImageFont.load_default()


def make_frame(bg_color, elements):
    """
    Create a single 1080x1920 frame with text elements.

    elements: list of dicts with keys:
        text, font_path, size, color, y, align ("center"/"left"), max_width
    """
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    for el in elements:
        font = load_font(el["font_path"], el["size"])
        text = el["text"]
        color = el["color"]
        y = el["y"]
        align = el.get("align", "center")
        max_w = el.get("max_width", W - 120)

        # Word wrap
        lines = []
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                lines.append("")
                continue
            wrapped = textwrap.fill(paragraph, width=el.get("wrap_width", 20))
            lines.extend(wrapped.split("\n"))

        current_y = y
        for line in lines:
            if not line.strip():
                current_y += el["size"] // 2
                continue
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            if align == "center":
                x = (W - tw) // 2
            elif align == "left":
                x = 60
            else:
                x = (W - tw) // 2
            draw.text((x, current_y), line, fill=color, font=font)
            current_y += th + el.get("line_spacing", 12)

    return img


def draw_logo(img, y_center):
    """Draw the Ask Anyway Campaign circle badge logo on an image."""
    draw = ImageDraw.Draw(img)

    # Circle ring
    cx, cy = W // 2, y_center
    radius = 160
    ring_width = 2
    for i in range(ring_width):
        draw.ellipse(
            [cx - radius - i, cy - radius - i, cx + radius + i, cy + radius + i],
            outline=TEAL,
            width=1,
        )

    # Gap at bottom of ring (open ring effect)
    gap_angle = 30
    draw.arc(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        start=90 - gap_angle // 2,
        end=90 + gap_angle // 2,
        fill=WARM_WHITE,
        width=ring_width + 2,
    )

    # Text inside ring
    font_the = load_font(FONT_REG, 22)
    font_ask = load_font(FONT_BLACK, 52)
    font_anyway = load_font(FONT_BLACK, 52)
    font_campaign = load_font(FONT_REG, 18)

    # THE
    bbox = draw.textbbox((0, 0), "THE", font=font_the)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, cy - 90), "THE", fill=TEAL, font=font_the)

    # ASK
    bbox = draw.textbbox((0, 0), "ASK", font=font_ask)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, cy - 60), "ASK", fill=TEAL, font=font_ask)

    # ANYWAY
    bbox = draw.textbbox((0, 0), "ANYWAY", font=font_anyway)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, cy + 2), "ANYWAY", fill=AMBER, font=font_anyway)

    # Amber divider line
    div_y = cy + 60
    div_w = 100
    draw.line([(cx - div_w // 2, div_y), (cx + div_w // 2, div_y)], fill=AMBER, width=2)

    # CAMPAIGN
    bbox = draw.textbbox((0, 0), "CAMPAIGN", font=font_campaign)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, cy + 70), "CAMPAIGN", fill=TEAL, font=font_campaign)

    return img


def pil_to_clip(img, duration):
    """Convert a PIL Image to a MoviePy ImageClip."""
    import numpy as np
    arr = np.array(img)
    return ImageClip(arr, duration=duration)


def build_intro_video():
    """Build the campaign introduction video with voiceover."""
    import json

    print("Building Ask Anyway Campaign intro video...")

    # Load voiceover manifest for timing
    vo_dir = ROOT / "output" / "videos" / "vo"
    manifest_path = vo_dir / "manifest.json"
    if manifest_path.exists():
        vo_manifest = json.loads(manifest_path.read_text())
        has_vo = True
        print("  Voiceover manifest loaded - syncing slide durations to audio")
    else:
        vo_manifest = {}
        has_vo = False
        print("  No voiceover found - using default durations")

    def slide_duration(slide_num, default):
        """Get duration from VO manifest or use default. Add 0.5s padding."""
        if has_vo and str(slide_num) in vo_manifest:
            return vo_manifest[str(slide_num)]["duration"] + 0.5
        return default

    clips = []

    # --- SLIDE 1: Hook (2.5s) ---
    frame1 = make_frame(TEAL_DARK, [
        {
            "text": "You don't need\ntraining to save\nsomeone's life.",
            "font_path": FONT_BLACK,
            "size": 72,
            "color": WARM_WHITE,
            "y": 650,
            "wrap_width": 18,
            "line_spacing": 16,
        },
    ])
    clips.append(pil_to_clip(frame1, slide_duration(1, 2.5)))

    # --- SLIDE 2: The tension ---
    frame2 = make_frame(WARM_WHITE, [
        {
            "text": "You just need\nthe courage to ask.",
            "font_path": FONT_BLACK,
            "size": 72,
            "color": TEAL,
            "y": 700,
            "wrap_width": 18,
            "line_spacing": 16,
        },
    ])
    clips.append(pil_to_clip(frame2, slide_duration(2, 2.5)))

    # --- SLIDE 3: The problem ---
    frame3 = make_frame(TEAL_DARK, [
        {
            "text": "Most people\ndon't ask because\nthey're afraid\nof saying\nthe wrong thing.",
            "font_path": FONT_BOLD,
            "size": 64,
            "color": WARM_WHITE,
            "y": 550,
            "wrap_width": 20,
            "line_spacing": 14,
        },
    ])
    clips.append(pil_to_clip(frame3, slide_duration(3, 3.0)))

    # --- SLIDE 4: The shift ---
    frame4 = make_frame(WARM_WHITE, [
        {
            "text": "But silence\nis scarier than\nthe wrong words.",
            "font_path": FONT_BLACK,
            "size": 72,
            "color": CHARCOAL,
            "y": 650,
            "wrap_width": 18,
            "line_spacing": 16,
        },
    ])
    clips.append(pil_to_clip(frame4, slide_duration(4, 2.5)))

    # --- SLIDE 5: What we built ---
    frame5 = make_frame(TEAL, [
        {
            "text": "We built a guide\nfor people who\ncare enough to\nask anyway.",
            "font_path": FONT_BOLD,
            "size": 64,
            "color": WARM_WHITE,
            "y": 600,
            "wrap_width": 22,
            "line_spacing": 14,
        },
    ])
    clips.append(pil_to_clip(frame5, slide_duration(5, 3.0)))

    # --- SLIDE 6: What you get ---
    frame6 = make_frame(WARM_WHITE, [
        {
            "text": "How to start\nthe conversation",
            "font_path": FONT_BLACK,
            "size": 56,
            "color": TEAL,
            "y": 480,
            "wrap_width": 22,
            "line_spacing": 10,
        },
        {
            "text": "How to stay in it\nwhen it gets hard",
            "font_path": FONT_BLACK,
            "size": 56,
            "color": TEAL,
            "y": 700,
            "wrap_width": 22,
            "line_spacing": 10,
        },
        {
            "text": "What to do next",
            "font_path": FONT_BLACK,
            "size": 56,
            "color": AMBER,
            "y": 920,
            "wrap_width": 22,
            "line_spacing": 10,
        },
    ])
    clips.append(pil_to_clip(frame6, slide_duration(6, 4.0)))

    # --- SLIDE 7: Credibility ---
    frame7 = make_frame(TEAL_DARK, [
        {
            "text": "Created by a\nlicensed clinical\nsocial worker\nand loss survivor.",
            "font_path": FONT_BOLD,
            "size": 58,
            "color": WARM_WHITE,
            "y": 600,
            "wrap_width": 22,
            "line_spacing": 14,
        },
        {
            "text": "Real talk. No jargon.\nJust what actually helps.",
            "font_path": FONT_REG,
            "size": 40,
            "color": AMBER,
            "y": 1050,
            "wrap_width": 30,
            "line_spacing": 8,
        },
    ])
    clips.append(pil_to_clip(frame7, slide_duration(7, 3.0)))

    # --- SLIDE 8: CTA with Logo ---
    frame8 = make_frame(WARM_WHITE, [])
    frame8 = draw_logo(frame8, 650)
    # Add CTA text below logo
    draw = ImageDraw.Draw(frame8)
    font_cta = load_font(FONT_BOLD, 44)
    cta_text = "Take the free quiz."
    bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 920), cta_text, fill=TEAL, font=font_cta)

    font_sub = load_font(FONT_REG, 34)
    sub_text = "Link in bio."
    bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 990), sub_text, fill=CHARCOAL, font=font_sub)

    # Crisis resources at bottom
    font_crisis = load_font(FONT_REG, 24)
    crisis1 = "988 Suicide & Crisis Lifeline: call or text 988"
    bbox = draw.textbbox((0, 0), crisis1, font=font_crisis)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 1680), crisis1, fill=CHARCOAL, font=font_crisis)

    crisis2 = "Crisis Text Line: text HOME to 741741"
    bbox = draw.textbbox((0, 0), crisis2, font=font_crisis)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 1720), crisis2, fill=CHARCOAL, font=font_crisis)

    clips.append(pil_to_clip(frame8, slide_duration(8, 4.0)))

    # --- COMPOSE ---
    print(f"  Composing {len(clips)} slides...")
    total_duration = sum(c.duration for c in clips)
    print(f"  Total duration: {total_duration:.1f}s")

    final = concatenate_videoclips(clips, method="compose")

    # Add voiceover audio if available
    if has_vo:
        import numpy as np

        # Load all VO clips, boost volume, and concatenate with silence padding
        audio_segments = []
        for i in range(1, 9):
            slide_dur = clips[i - 1].duration
            vo_file = vo_dir / f"slide-{i:02d}.mp3"
            if vo_file.exists():
                ac = AudioFileClip(str(vo_file))
                # Read raw audio, amplify 5x, clamp to [-1, 1]
                raw = ac.to_soundarray(fps=44100)
                boosted = np.clip(raw * 5.0, -1.0, 1.0)
                # Pad with silence to fill the slide duration
                total_samples = int(slide_dur * 44100)
                if total_samples > len(boosted):
                    pad = np.zeros((total_samples - len(boosted), boosted.shape[1]))
                    boosted = np.concatenate([boosted, pad])
                else:
                    boosted = boosted[:total_samples]
                audio_segments.append(boosted)
                ac.close()
            else:
                # No VO for this slide - add silence
                total_samples = int(slide_dur * 44100)
                audio_segments.append(np.zeros((total_samples, 2)))

        full_audio = np.concatenate(audio_segments)

        from moviepy.audio.AudioClip import AudioClip

        def make_audio_frame(t):
            # t can be a single float or array of floats
            indices = np.int64(np.array(t) * 44100)
            indices = np.clip(indices, 0, len(full_audio) - 1)
            return full_audio[indices]

        combined = AudioClip(make_audio_frame, duration=total_duration, fps=44100)
        combined.nchannels = 2
        final = final.with_audio(combined)
        print("  Voiceover audio attached (volume boosted 5x)")

    output_path = str(OUTPUT_DIR / "ask-anyway-campaign-intro.mp4")
    print(f"  Rendering to {output_path}...")

    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac" if has_vo else None,
        preset="medium",
        logger="bar",
    )

    file_size = os.path.getsize(output_path)
    print(f"\nDone! Video saved to {output_path}")
    print(f"  Duration: {total_duration}s")
    print(f"  Resolution: {W}x{H}")
    print(f"  File size: {file_size / 1024:.0f} KB")


if __name__ == "__main__":
    build_intro_video()
