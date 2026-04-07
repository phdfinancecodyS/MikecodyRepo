#!/usr/bin/env python3
"""
Ask Anyway Campaign Video v2  - TikTok-optimized.

Changes from v1:
- 6 slides instead of 8, ~22s total
- Text fade-in animations
- Ken Burns (subtle zoom) on every slide
- Cross-dissolve transitions
- Punchy 2-5 word text per frame
- Ambient music bed under voiceover
- Tighter pacing
"""
import json
import os
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    ColorClip,
)
from moviepy.video.fx import CrossFadeIn, CrossFadeOut

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "assets" / "fonts"
OUTPUT_DIR = ROOT / "output" / "videos"
VO_DIR = ROOT / "output" / "videos" / "vo2"

# Brand colors
TEAL = (26, 107, 106)
AMBER = (212, 146, 42)
WARM_WHITE = (250, 247, 242)
CHARCOAL = (45, 45, 45)
TEAL_DARK = (15, 78, 77)
NEAR_BLACK = (18, 18, 18)

W, H = 1080, 1920
FPS = 30

FONT_BLACK = str(FONTS_DIR / "Montserrat-Black.ttf")
FONT_BOLD = str(FONTS_DIR / "Montserrat-Bold.ttf")
FONT_REG = str(FONTS_DIR / "Montserrat-Regular.ttf")


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        return ImageFont.load_default()


def render_text_frame(bg_color, lines, text_color, font_path, font_size,
                      y_start=None, line_spacing=20, highlight_word=None,
                      highlight_color=AMBER):
    """Render a frame with centered text lines. Returns PIL Image."""
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)
    font = load_font(font_path, font_size)

    # Calculate total text height to center vertically
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])
    total_h = sum(line_heights) + line_spacing * (len(lines) - 1)

    if y_start is None:
        y = (H - total_h) // 2
    else:
        y = y_start

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (W - tw) // 2

        if highlight_word and highlight_word.lower() in line.lower():
            # Draw with highlight on the specific word
            parts_before = line[:line.lower().index(highlight_word.lower())]
            parts_hl = line[line.lower().index(highlight_word.lower()):
                           line.lower().index(highlight_word.lower()) + len(highlight_word)]
            parts_after = line[line.lower().index(highlight_word.lower()) + len(highlight_word):]

            # Draw the whole line first, then overlay highlight word
            draw.text((x, y), line, fill=text_color, font=font)
            if parts_before:
                bw = draw.textbbox((0, 0), parts_before, font=font)[2]
            else:
                bw = 0
            draw.text((x + bw, y), parts_hl, fill=highlight_color, font=font)
        else:
            draw.text((x, y), line, fill=text_color, font=font)

        y += th + line_spacing

    return img


def draw_logo_on(img):
    """Draw the Ask Anyway circle badge logo."""
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, 700
    radius = 140
    for i in range(2):
        draw.ellipse(
            [cx - radius - i, cy - radius - i, cx + radius + i, cy + radius + i],
            outline=TEAL, width=1,
        )
    # Gap
    draw.arc(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        start=75, end=105, fill=WARM_WHITE, width=4,
    )
    # Text
    font_the = load_font(FONT_REG, 20)
    font_ask = load_font(FONT_BLACK, 46)
    font_anyway = load_font(FONT_BLACK, 46)
    font_campaign = load_font(FONT_REG, 16)

    for text, font, color, ty in [
        ("THE", font_the, TEAL, cy - 80),
        ("ASK", font_ask, TEAL, cy - 55),
        ("ANYWAY", font_anyway, AMBER, cy + 2),
        ("CAMPAIGN", font_campaign, TEAL, cy + 62),
    ]:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, ty), text, fill=color, font=font)

    # Amber divider
    draw.line([(cx - 45, cy + 55), (cx + 45, cy + 55)], fill=AMBER, width=2)
    return img


def make_zoom_clip(pil_img, duration, zoom_start=1.0, zoom_end=1.04):
    """Create a clip with slow Ken Burns zoom effect."""
    base_arr = np.array(pil_img)
    bh, bw = base_arr.shape[:2]

    def make_frame(t):
        progress = t / duration if duration > 0 else 0
        scale = zoom_start + (zoom_end - zoom_start) * progress
        # Crop from center at current scale
        cw = int(bw / scale)
        ch = int(bh / scale)
        x1 = (bw - cw) // 2
        y1 = (bh - ch) // 2
        cropped = base_arr[y1:y1 + ch, x1:x1 + cw]
        # Resize back to full resolution
        from PIL import Image as PILImage
        resized = PILImage.fromarray(cropped).resize((bw, bh), PILImage.LANCZOS)
        return np.array(resized)

    from moviepy import VideoClip
    clip = VideoClip(make_frame, duration=duration)
    return clip


def make_fade_text_clip(pil_bg, pil_text_img, duration, fade_dur=0.4):
    """Create a clip where text fades in over a background with zoom."""
    bg_arr = np.array(pil_bg)
    text_arr = np.array(pil_text_img)
    bh, bw = bg_arr.shape[:2]

    def make_frame(t):
        progress = t / duration if duration > 0 else 0
        # Ken Burns zoom
        scale = 1.0 + 0.03 * progress
        cw = int(bw / scale)
        ch = int(bh / scale)
        x1 = (bw - cw) // 2
        y1 = (bh - ch) // 2

        # Text fade-in
        if t < fade_dur:
            alpha = t / fade_dur
        else:
            alpha = 1.0

        # Blend: lerp between bg and text frame based on alpha
        bg_crop = bg_arr[y1:y1 + ch, x1:x1 + cw]
        tx_crop = text_arr[y1:y1 + ch, x1:x1 + cw]

        from PIL import Image as PILImage
        bg_resized = np.array(PILImage.fromarray(bg_crop).resize((bw, bh), PILImage.LANCZOS))
        tx_resized = np.array(PILImage.fromarray(tx_crop).resize((bw, bh), PILImage.LANCZOS))

        blended = (bg_resized * (1 - alpha) + tx_resized * alpha).astype(np.uint8)
        return blended

    from moviepy import VideoClip
    return VideoClip(make_frame, duration=duration)


def build_v2():
    """Build the v2 campaign video."""
    print("Building Ask Anyway Campaign v2...")

    # Load VO manifest
    manifest = json.loads((VO_DIR / "manifest.json").read_text())

    def slide_dur(n, pad=0.3):
        return manifest[str(n)]["duration"] + pad

    slides = []

    # --- SLIDE 1: HOOK --- "Nobody teaches you this."
    dur1 = slide_dur(1, 0.5)
    bg1 = Image.new("RGB", (W, H), NEAR_BLACK)
    txt1 = render_text_frame(
        NEAR_BLACK,
        ["Nobody", "teaches you", "this."],
        WARM_WHITE, FONT_BLACK, 90,
        highlight_word="this",
        highlight_color=AMBER,
    )
    slides.append(make_fade_text_clip(bg1, txt1, dur1, fade_dur=0.3))

    # --- SLIDE 2 --- "What to say when someone you love is struggling."
    dur2 = slide_dur(2, 0.3)
    bg2 = Image.new("RGB", (W, H), WARM_WHITE)
    txt2 = render_text_frame(
        WARM_WHITE,
        ["What to say", "when someone", "you love", "is struggling."],
        CHARCOAL, FONT_BOLD, 72,
        highlight_word="struggling",
        highlight_color=TEAL,
    )
    slides.append(make_fade_text_clip(bg2, txt2, dur2, fade_dur=0.35))

    # --- SLIDE 3 --- "You're not afraid of saying the wrong thing..."
    dur3 = slide_dur(3, 0.3)
    bg3 = Image.new("RGB", (W, H), TEAL_DARK)
    txt3 = render_text_frame(
        TEAL_DARK,
        ["You're not afraid", "of saying the", "wrong thing.", "", "You're afraid", "of saying", "nothing."],
        WARM_WHITE, FONT_BOLD, 64,
        highlight_word="nothing",
        highlight_color=AMBER,
    )
    slides.append(make_fade_text_clip(bg3, txt3, dur3, fade_dur=0.4))

    # --- SLIDE 4 --- "So we built you a guide."
    dur4 = slide_dur(4, 0.3)
    bg4 = Image.new("RGB", (W, H), TEAL)
    txt4 = render_text_frame(
        TEAL,
        ["So we built", "you a guide."],
        WARM_WHITE, FONT_BLACK, 84,
    )
    slides.append(make_fade_text_clip(bg4, txt4, dur4, fade_dur=0.25))

    # --- SLIDE 5 --- Credibility (new phrasing)
    dur5 = slide_dur(5, 0.5)
    bg5 = Image.new("RGB", (W, H), NEAR_BLACK)
    txt5 = render_text_frame(
        NEAR_BLACK,
        ["Created by a", "licensed therapist", "who knows what", "it's like to wish", "she'd asked", "sooner."],
        WARM_WHITE, FONT_BOLD, 58,
        highlight_word="sooner",
        highlight_color=AMBER,
    )
    slides.append(make_fade_text_clip(bg5, txt5, dur5, fade_dur=0.4))

    # --- SLIDE 6 --- CTA + Logo
    dur6 = slide_dur(6, 1.0)  # extra hold on CTA
    cta_frame = Image.new("RGB", (W, H), WARM_WHITE)
    cta_frame = draw_logo_on(cta_frame)
    draw = ImageDraw.Draw(cta_frame)

    # CTA text
    font_cta = load_font(FONT_BOLD, 44)
    for text, color, y in [
        ("Take the free quiz.", TEAL, 920),
        ("Link in bio.", CHARCOAL, 985),
    ]:
        bbox = draw.textbbox((0, 0), text, font=font_cta)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, y), text, fill=color, font=font_cta)

    # Crisis resources
    font_cr = load_font(FONT_REG, 22)
    for text, y in [
        ("988 Suicide & Crisis Lifeline: call or text 988", 1680),
        ("Crisis Text Line: text HOME to 741741", 1716),
    ]:
        bbox = draw.textbbox((0, 0), text, font=font_cr)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, y), text, fill=CHARCOAL, font=font_cr)

    bg6 = Image.new("RGB", (W, H), WARM_WHITE)
    slides.append(make_fade_text_clip(bg6, cta_frame, dur6, fade_dur=0.35))

    # Compose with cross-dissolve
    print(f"  Composing {len(slides)} slides...")
    xfade = 0.25  # cross-dissolve duration

    # Apply crossfade effects
    processed = []
    for i, clip in enumerate(slides):
        c = clip
        if i > 0:
            c = c.with_effects([CrossFadeIn(xfade)])
        if i < len(slides) - 1:
            c = c.with_effects([CrossFadeOut(xfade)])
        processed.append(c)

    final = concatenate_videoclips(processed, method="compose", padding=-xfade)
    total_dur = final.duration
    print(f"  Total duration: {total_dur:.1f}s")

    # Render video without audio first
    silent_path = str(OUTPUT_DIR / "v2_silent.mp4")
    print(f"  Rendering silent video...")
    final.write_videofile(
        silent_path,
        fps=FPS,
        codec="libx264",
        preset="medium",
        logger="bar",
    )

    print(f"  Silent video: {os.path.getsize(silent_path) / 1024:.0f} KB")
    print(f"  Duration: {total_dur:.1f}s")
    print("  Now merge audio with _merge_audio_v2.py")


if __name__ == "__main__":
    build_v2()
