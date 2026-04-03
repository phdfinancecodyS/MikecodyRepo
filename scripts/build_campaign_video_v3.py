#!/usr/bin/env python3
"""
Ask Anyway Campaign Video v3 — frame-by-frame renderer.

Renders every frame with PIL, pipes raw RGB to ffmpeg.
No MoviePy composition = no broken audio or missing animations.

Features:
- Text fade-in on each slide
- Ken Burns (slow zoom) on every slide
- Cross-dissolve between slides
- Logo watermark that builds in opacity throughout the video
- Amber highlight on key words
"""
import json
import math
import os
import subprocess
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe

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

# Warmer palette for gradients
WARM_BLACK = (22, 20, 18)       # warm-tinted dark
WARM_BLACK_2 = (35, 28, 24)    # slightly lighter warm dark
CREAM = (252, 248, 240)        # softer cream
CREAM_2 = (245, 238, 225)      # slightly deeper warm cream
TEAL_MID = (20, 92, 90)        # mid teal for gradients
AMBER_SOFT = (220, 170, 80)    # softer amber for accents
AMBER_GLOW = (255, 200, 100)   # warm glow accent

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


def lerp_color(c1, c2, t):
    """Linearly interpolate between two RGB tuples. t=0 -> c1, t=1 -> c2."""
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def render_gradient(color_top, color_bottom, w=W, h=H):
    """Render a vertical gradient. Returns PIL Image."""
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        t = y / (h - 1)
        arr[y, :] = lerp_color(color_top, color_bottom, t)
    return Image.fromarray(arr)


def render_radial_gradient(center_color, edge_color, w=W, h=H, cx=None, cy=None):
    """Render a radial gradient centered on (cx, cy). Returns PIL Image."""
    if cx is None:
        cx = w // 2
    if cy is None:
        cy = h // 2
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    max_dist = math.sqrt(cx ** 2 + cy ** 2) * 1.2
    ys, xs = np.mgrid[0:h, 0:w]
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    t = np.clip(dist / max_dist, 0, 1)
    for c in range(3):
        arr[:, :, c] = (center_color[c] * (1 - t) + edge_color[c] * t).astype(np.uint8)
    return Image.fromarray(arr)


def apply_vignette(img_arr, strength=0.4):
    """Apply a warm vignette (darkened edges). Operates on numpy RGB array."""
    h, w = img_arr.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w]
    cx, cy = w / 2, h / 2
    max_dist = math.sqrt(cx ** 2 + cy ** 2)
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / max_dist
    # Smooth falloff starting at 60% of the way to the edge
    vignette = 1.0 - strength * np.clip((dist - 0.5) / 0.5, 0, 1) ** 1.5
    vignette = vignette[:, :, np.newaxis]
    return (img_arr.astype(float) * vignette).clip(0, 255).astype(np.uint8)


def apply_grain(img_arr, amount=8):
    """Add subtle warm film grain to a numpy RGB array."""
    noise = np.random.normal(0, amount, img_arr.shape).astype(np.int16)
    # Warm the grain: slightly more in red channel, less in blue
    noise[:, :, 0] = (noise[:, :, 0] * 1.15).astype(np.int16)
    noise[:, :, 2] = (noise[:, :, 2] * 0.8).astype(np.int16)
    result = img_arr.astype(np.int16) + noise
    return result.clip(0, 255).astype(np.uint8)


def draw_accent_dots(draw, y_center, color, count=5, spacing=30, radius=3):
    """Draw a row of small decorative dots centered horizontally."""
    total_w = (count - 1) * spacing
    start_x = (W - total_w) // 2
    for i in range(count):
        x = start_x + i * spacing
        draw.ellipse([x - radius, y_center - radius, x + radius, y_center + radius],
                     fill=color)


def draw_accent_line(draw, y, color, width=120, thickness=2):
    """Draw a thin centered horizontal accent line."""
    x1 = (W - width) // 2
    draw.line([(x1, y), (x1 + width, y)], fill=color, width=thickness)


def render_text_image(bg_color, lines, text_color, font_path, font_size,
                      line_spacing=20, highlight_word=None, highlight_color=AMBER,
                      y_offset=0, subtitle=None, gradient=None, accents=True):
    """Render text lines centered on a gradient/colored background.
    gradient: (top_color, bottom_color) or None for flat bg.
    Returns PIL Image.
    """
    if gradient:
        img = render_gradient(gradient[0], gradient[1])
    else:
        img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)
    font = load_font(font_path, font_size)

    # Measure lines
    line_data = []
    for line in lines:
        if line == "":
            line_data.append(("", 0, int(font_size * 0.4)))
            continue
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        line_data.append((line, tw, th))

    total_h = sum(ld[2] for ld in line_data) + line_spacing * (len(line_data) - 1)
    y = (H - total_h) // 2 + y_offset

    # Decorative accent line above text block
    if accents:
        draw_accent_line(draw, y - 50, (*AMBER_SOFT, ), width=100, thickness=2)

    for line_text, tw, th in line_data:
        if line_text == "":
            y += th + line_spacing
            continue
        x = (W - tw) // 2

        if highlight_word and highlight_word.lower() in line_text.lower():
            idx = line_text.lower().index(highlight_word.lower())
            before = line_text[:idx]
            hl = line_text[idx:idx + len(highlight_word)]
            draw.text((x, y), line_text, fill=text_color, font=font)
            if before:
                bw = draw.textbbox((0, 0), before, font=font)[2]
            else:
                bw = 0
            draw.text((x + bw, y), hl, fill=highlight_color, font=font)
        else:
            draw.text((x, y), line_text, fill=text_color, font=font)

        y += th + line_spacing

    # Decorative accent line below text block
    if accents:
        draw_accent_line(draw, y + 20, (*AMBER_SOFT, ), width=100, thickness=2)

    # Optional subtitle below main text
    if subtitle:
        sub_font = load_font(FONT_REG, 32)
        sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
        sub_tw = sub_bbox[2] - sub_bbox[0]
        sub_y = y + 60
        draw_accent_dots(draw, sub_y - 20, AMBER_SOFT, count=3, spacing=20, radius=3)
        draw.text(((W - sub_tw) // 2, sub_y), subtitle, fill=AMBER_SOFT, font=sub_font)

    # Apply grain + vignette
    arr = np.array(img)
    arr = apply_grain(arr, amount=6)
    arr = apply_vignette(arr, strength=0.35)
    return Image.fromarray(arr)


def render_logo_watermark(opacity=0.15):
    """Render the logo badge on a transparent-compatible image. Returns RGBA."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Position: bottom-center, above crisis resources area
    cx, cy = W // 2, H - 300
    radius = 140
    alpha_byte = int(opacity * 255)

    # Circle ring — thicker line
    ring_color = (*TEAL, alpha_byte)
    for i in range(3):
        draw.ellipse(
            [cx - radius - i, cy - radius - i, cx + radius + i, cy + radius + i],
            outline=ring_color, width=2,
        )

    # Text inside — 2x font sizes
    font_the = load_font(FONT_REG, 20)
    font_ask = load_font(FONT_BLACK, 46)
    font_anyway = load_font(FONT_BLACK, 46)
    font_campaign = load_font(FONT_REG, 16)

    teal_a = (*TEAL, alpha_byte)
    amber_a = (*AMBER, alpha_byte)

    for text, font, color, ty in [
        ("THE", font_the, teal_a, cy - 80),
        ("ASK", font_ask, teal_a, cy - 55),
        ("ANYWAY", font_anyway, amber_a, cy + 2),
        ("CAMPAIGN", font_campaign, teal_a, cy + 62),
    ]:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, ty), text, fill=color, font=font)

    return img


def draw_cta_logo(img):
    """Draw the full-size CTA logo on slide 6."""
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, 700
    radius = 140

    # Subtle amber glow behind the ring
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for r in range(radius + 60, radius, -2):
        alpha = int(12 * (1 - (r - radius) / 60))
        glow_draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                          fill=(*AMBER_SOFT, max(alpha, 0)))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)

    for i in range(2):
        draw.ellipse(
            [cx - radius - i, cy - radius - i, cx + radius + i, cy + radius + i],
            outline=TEAL, width=1,
        )
    # Gap at bottom
    draw.arc(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        start=75, end=105, fill=WARM_WHITE, width=4,
    )

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

    # CTA text
    font_cta = load_font(FONT_BOLD, 44)
    font_sub = load_font(FONT_REG, 38)
    for text, font, color, y in [
        ("Take the free quiz.", font_cta, TEAL, 920),
        ("Link in bio.", font_sub, CHARCOAL, 985),
    ]:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, y), text, fill=color, font=font)

    # Crisis resources
    font_cr = load_font(FONT_REG, 22)
    for text, y in [
        ("988 Suicide & Crisis Lifeline: call or text 988", 1700),
        ("Crisis Text Line: text HOME to 741741", 1736),
    ]:
        bbox = draw.textbbox((0, 0), text, font=font_cr)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, y), text, fill=CHARCOAL, font=font_cr)

    return img


def apply_zoom(img_arr, progress, max_zoom=0.04):
    """Apply Ken Burns zoom. progress: 0.0 to 1.0."""
    scale = 1.0 + max_zoom * progress
    bh, bw = img_arr.shape[:2]
    cw = int(bw / scale)
    ch = int(bh / scale)
    x1 = (bw - cw) // 2
    y1 = (bh - ch) // 2
    cropped = img_arr[y1:y1 + ch, x1:x1 + cw]
    resized = Image.fromarray(cropped).resize((bw, bh), Image.LANCZOS)
    return np.array(resized)


# ── Stick-figure animation for slides 1-3 ──────────────────────────
# Real kitchen photo background + LARGE fluid stick figure
# Natural joint mechanics using inverse kinematics
# Knife contacts cutting board — gravity-physics chop arc

# ── Chibi style: big head, pill body, stick limbs ──
OUTLINE_COLOR = (55, 48, 42)     # warm dark brown outline
BODY_FILL = (240, 235, 225)      # warm white body fill
SKIN_COLOR = (252, 245, 235)     # face / hands
OUTLINE_W = 4

# ── Figure scale ── change this ONE number to resize everything ──
S = 3.0
HEAD_R = int(65 * S)             # 195 — big chibi head
BODY_RX = int(32 * S)           # pill body half-width = 96
BODY_RY = int(40 * S)           # pill body half-height = 120
UPPER_ARM_LEN = int(70 * S)     # 210
FOREARM_LEN = int(60 * S)       # 180
UPPER_LEG_LEN = int(55 * S)     # 165
LOWER_LEG_LEN = int(50 * S)     # 150
LW = max(4, int(4 * S * 0.7))   # ~8 — thinner stick limbs
SHADOW_OFF = max(3, int(4 * S * 0.6))   # 7

# Kitchen layout
COUNTER_Y = int(H * 0.68)       # counter surface = ~1306
COUNTER_HEIGHT = 80
BODY_CY = COUNTER_Y - BODY_RY - int(45 * S)  # body center
BODY_TOP = BODY_CY - BODY_RY
BODY_BOTTOM = BODY_CY + BODY_RY
HEAD_CY_BASE = BODY_TOP - HEAD_R - int(2 * S)
SHOULDER_Y_BASE = BODY_TOP + int(10 * S)      # arms attach at top of body
HIP_Y_BASE = BODY_BOTTOM
FIGURE_CX = W // 2

# ── Legacy aliases for compatibility ──
FIGURE_COLOR = OUTLINE_COLOR
FIGURE_SHADOW = (25, 22, 18)

# Load and prepare kitchen background photo (once)
_kitchen_bg_cache = None
_paper_texture_cache = None


def generate_paper_texture(w=W, h=H):
    """Generate a subtle crumpled-paper texture overlay.
    Returns numpy array (h, w) with brightness values 0-255.
    Applied as a multiply blend to add paper grain/wrinkles."""
    global _paper_texture_cache
    if _paper_texture_cache is not None:
        return _paper_texture_cache
    np.random.seed(42)  # deterministic texture
    # Multi-scale Perlin-like noise for paper wrinkles
    texture = np.ones((h, w), dtype=np.float32) * 235

    # Large-scale wrinkles
    for scale in [200, 80, 30]:
        sh = max(2, h // scale)
        sw = max(2, w // scale)
        noise = np.random.normal(0, 1, (sh, sw)).astype(np.float32)
        noise_img = Image.fromarray((noise * 127 + 128).clip(0, 255).astype(np.uint8))
        noise_up = np.array(noise_img.resize((w, h), Image.BILINEAR), dtype=np.float32)
        weight = 8.0 / (scale / 30.0)
        texture += (noise_up - 128) * weight / 128

    # Fine grain
    fine_noise = np.random.normal(0, 3, (h, w)).astype(np.float32)
    texture += fine_noise

    texture = texture.clip(200, 255).astype(np.uint8)
    _paper_texture_cache = texture
    return texture


def apply_paper_texture(img_arr, opacity=0.12):
    """Blend paper texture onto image for organic hand-drawn feel.
    opacity: 0 = no effect, 1 = full paper overlay."""
    paper = generate_paper_texture(img_arr.shape[1], img_arr.shape[0])
    # Convert paper to 3-channel
    paper_rgb = np.stack([paper, paper, paper], axis=2).astype(np.float32) / 255.0
    base = img_arr.astype(np.float32)
    # Soft-light blend: subtle texture without washing out the image
    result = base * (1.0 - opacity) + base * paper_rgb * opacity * (255.0 / 230.0)
    return result.clip(0, 255).astype(np.uint8)


def get_kitchen_bg():
    """Draw a cartoon-style kitchen background matching the chibi character style."""
    global _kitchen_bg_cache
    if _kitchen_bg_cache is not None:
        return _kitchen_bg_cache

    img = Image.new("RGB", (W, H), (245, 240, 232))
    draw = ImageDraw.Draw(img)

    # ── Wall — warm gradient ──
    wall_bottom = COUNTER_Y
    for y in range(wall_bottom):
        t = y / wall_bottom
        r = int(248 - t * 12)
        g = int(242 - t * 10)
        b = int(232 - t * 8)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── Backsplash tile pattern ──
    tile_top = COUNTER_Y - int(220 * S)
    tile_bottom = COUNTER_Y
    tile_color = (235, 230, 218)
    tile_grout = (215, 208, 195)
    tile_w, tile_h = int(45 * S), int(35 * S)
    for row_i, ty in enumerate(range(tile_top, tile_bottom, tile_h)):
        offset = tile_w // 2 if row_i % 2 else 0
        for tx in range(-tile_w + offset, W + tile_w, tile_w):
            draw.rounded_rectangle([tx + 2, ty + 2, tx + tile_w - 2, ty + tile_h - 2],
                                   radius=int(3 * S), fill=tile_color,
                                   outline=tile_grout, width=1)

    # ── Upper cabinets ──
    cab_color = (200, 185, 165)
    cab_outline = (160, 145, 125)
    cab_w = int(130 * S)
    cab_h = int(100 * S)
    cab_y = tile_top - cab_h - int(20 * S)
    for cab_cx in [int(W * 0.2), int(W * 0.8)]:
        # Shadow
        draw.rounded_rectangle([cab_cx - cab_w//2 + 4, cab_y + 4,
                                cab_cx + cab_w//2 + 4, cab_y + cab_h + 4],
                               radius=int(8 * S), fill=(180, 170, 155))
        # Cabinet body
        draw.rounded_rectangle([cab_cx - cab_w//2, cab_y,
                                cab_cx + cab_w//2, cab_y + cab_h],
                               radius=int(8 * S), fill=cab_color,
                               outline=cab_outline, width=max(2, int(2 * S * 0.5)))
        # Panel detail
        inset = int(12 * S)
        draw.rounded_rectangle([cab_cx - cab_w//2 + inset, cab_y + inset,
                                cab_cx + cab_w//2 - inset, cab_y + cab_h - inset],
                               radius=int(4 * S), outline=cab_outline, width=1)
        # Handle
        handle_y = cab_y + cab_h - int(20 * S)
        draw.rounded_rectangle([cab_cx - int(8 * S), handle_y,
                                cab_cx + int(8 * S), handle_y + int(4 * S)],
                               radius=int(2 * S), fill=(170, 155, 135))

    # ── Range hood (center) ──
    hood_w = int(120 * S)
    hood_h = int(50 * S)
    hood_y = tile_top - int(15 * S)
    draw.rounded_rectangle([W//2 - hood_w//2, hood_y - hood_h,
                            W//2 + hood_w//2, hood_y],
                           radius=int(6 * S), fill=(195, 188, 175),
                           outline=cab_outline, width=max(2, int(2 * S * 0.5)))
    # Hood vent lines
    for i in range(3):
        vy = hood_y - hood_h + int(15 * S) + i * int(10 * S)
        draw.line([(W//2 - hood_w//3, vy), (W//2 + hood_w//3, vy)],
                  fill=(180, 172, 158), width=1)

    # ── Floor — below counter ──
    floor_top = COUNTER_Y + COUNTER_HEIGHT
    floor_color_a = (215, 200, 175)
    floor_color_b = (205, 190, 165)
    floor_tile = int(60 * S)
    for row, fy in enumerate(range(floor_top, H, floor_tile)):
        for col, fx in enumerate(range(0, W, floor_tile)):
            fc = floor_color_a if (row + col) % 2 == 0 else floor_color_b
            draw.rectangle([fx, fy, fx + floor_tile, fy + floor_tile], fill=fc)
            draw.rectangle([fx, fy, fx + floor_tile, fy + floor_tile],
                           outline=(195, 180, 155), width=1)

    # ── Window (upper right) ──
    win_cx = int(W * 0.82)
    win_cy = cab_y + cab_h // 2
    win_w, win_h = int(60 * S), int(70 * S)
    # Window glow
    draw.rounded_rectangle([win_cx - win_w//2 - 3, win_cy - win_h//2 - 3,
                            win_cx + win_w//2 + 3, win_cy + win_h//2 + 3],
                           radius=int(4 * S), fill=(220, 225, 235))
    draw.rounded_rectangle([win_cx - win_w//2, win_cy - win_h//2,
                            win_cx + win_w//2, win_cy + win_h//2],
                           radius=int(4 * S), fill=(200, 220, 240),
                           outline=cab_outline, width=max(2, int(2 * S * 0.5)))
    # Window cross
    draw.line([(win_cx, win_cy - win_h//2), (win_cx, win_cy + win_h//2)],
              fill=cab_outline, width=max(2, int(2 * S * 0.4)))
    draw.line([(win_cx - win_w//2, win_cy), (win_cx + win_w//2, win_cy)],
              fill=cab_outline, width=max(2, int(2 * S * 0.4)))

    arr = np.array(img)
    _kitchen_bg_cache = arr
    return _kitchen_bg_cache


def ease_in_out(t):
    """Smooth easing — slow start, fast middle, slow end."""
    return t * t * (3 - 2 * t)


def ease_sin(t, freq=1.0, phase=0.0):
    """Smooth sinusoidal oscillation."""
    return math.sin(t * math.pi * 2 * freq + phase)


def ik_arm(shoulder, target, upper_len, lower_len, bend_dir=-1):
    """2-joint inverse kinematics: compute elbow so hand reaches target.
    bend_dir: -1 = elbow bends left/up, +1 = elbow bends right/down.
    """
    dx = target[0] - shoulder[0]
    dy = target[1] - shoulder[1]
    dist = math.sqrt(dx * dx + dy * dy)
    max_reach = upper_len + lower_len - 2
    if dist > max_reach:
        s = max_reach / dist
        dx, dy = dx * s, dy * s
        dist = max_reach
    min_reach = abs(upper_len - lower_len) + 1
    if dist < min_reach:
        s = min_reach / dist
        dx, dy = dx * s, dy * s
        dist = min_reach
    cos_a = (upper_len ** 2 + dist ** 2 - lower_len ** 2) / (2 * upper_len * dist)
    cos_a = max(-1.0, min(1.0, cos_a))
    angle_a = math.acos(cos_a)
    angle_to_target = math.atan2(dy, dx)
    elbow_angle = angle_to_target + bend_dir * angle_a
    ex = shoulder[0] + int(upper_len * math.cos(elbow_angle))
    ey = shoulder[1] + int(upper_len * math.sin(elbow_angle))
    return (ex, ey)


def _wobble_point(p, amount=2.5):
    """Add slight random displacement to a point for hand-drawn feel."""
    return (p[0] + int(np.random.normal(0, amount)),
            p[1] + int(np.random.normal(0, amount)))


def _hand_drawn_line(draw, p1, p2, fill, width, segments=5, wobble=True):
    """Draw a line with subtle hand-drawn wobble — multiple sub-segments
    with slight random displacement at each control point."""
    pts = []
    for i in range(segments + 1):
        t = i / segments
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        if wobble and 0 < i < segments:  # don't wobble endpoints
            wobble = max(1.5, width * 0.15)
            x += np.random.normal(0, wobble)
            y += np.random.normal(0, wobble)
        pts.append((int(x), int(y)))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=fill, width=width)


def draw_limb_seg(draw, p1, p2, color=FIGURE_COLOR, width=LW,
                  shadow=True, shadow_color=FIGURE_SHADOW):
    """Draw a limb segment with drop shadow and tight joint caps.
    Limb strokes are deliberately non-wobbly to prevent shaking.
    """
    if shadow:
        _hand_drawn_line(draw,
                         (p1[0] + SHADOW_OFF, p1[1] + SHADOW_OFF),
                         (p2[0] + SHADOW_OFF, p2[1] + SHADOW_OFF),
                         shadow_color, width, wobble=False)
        # Cap joints to avoid tiny gaps where segments meet.
        sr = max(1, width // 3)
        draw.ellipse([
            p1[0] + SHADOW_OFF - sr, p1[1] + SHADOW_OFF - sr,
            p1[0] + SHADOW_OFF + sr, p1[1] + SHADOW_OFF + sr,
        ], fill=shadow_color)
        draw.ellipse([
            p2[0] + SHADOW_OFF - sr, p2[1] + SHADOW_OFF - sr,
            p2[0] + SHADOW_OFF + sr, p2[1] + SHADOW_OFF + sr,
        ], fill=shadow_color)
    _hand_drawn_line(draw, p1, p2, color, width, wobble=False)
    r = max(1, width // 3)
    draw.ellipse([p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r], fill=color)
    draw.ellipse([p2[0] - r, p2[1] - r, p2[0] + r, p2[1] + r], fill=color)


def chop_curve(t, freq=2.0):
    """Knife height above board: 0=contact, 1=max raise.
    Physics: slow raise, gravity fall, impact bounce.
    """
    cycle = (t * freq) % 1.0
    if cycle < 0.38:
        rt = cycle / 0.38
        return ease_in_out(rt)
    elif cycle < 0.68:
        ft = (cycle - 0.38) / 0.30
        return 1.0 - ft * ft
    elif cycle < 0.80:
        bt = (cycle - 0.68) / 0.12
        return 0.06 * math.sin(bt * math.pi)
    else:
        return 0.0


def draw_fluid_figure(draw, cx, pose, t, counter_y):
    """Draw a chibi-style figure: big round head, small pill body, stick limbs.
    IK-driven arms, expressive face with blinks and lip sync.
    """
    outline = OUTLINE_COLOR
    shadow_c = FIGURE_SHADOW

    # ══ Multi-frequency overlapping motion ══
    breath = ease_sin(t, freq=1.2) * int(4 * S)
    weight_shift = ease_sin(t, freq=0.7, phase=0.5) * int(5 * S)
    head_bob = ease_sin(t, freq=1.8, phase=1.0) * int(3 * S)
    micro_sway = ease_sin(t, freq=2.3, phase=2.1) * int(1 * S)

    # ─── Pose-specific lean ───
    if pose == "chop":
        kh = chop_curve(t, freq=2.0)
        lean = int((1.0 - kh) * 8 * S)
        head_tilt_x = int((1.0 - kh) * 5 * S)
    elif pose == "stir":
        lean = int(ease_sin(t, freq=0.9) * 5 * S)
        head_tilt_x = int(ease_sin(t, freq=0.9, phase=0.3) * 3 * S)
    else:
        lean = int(ease_sin(t, freq=0.3) * 2 * S)
        head_tilt_x = int(ease_sin(t, freq=0.4, phase=0.2) * 2 * S)

    # ══ Body position ══
    body_cy = int(BODY_CY + breath * 0.3)
    body_top = body_cy - BODY_RY
    body_bottom = body_cy + BODY_RY

    body_cx = cx + int(weight_shift * 0.3) + lean
    # Shoulder attach points (sides of pill body near top)
    l_shoulder = (body_cx - BODY_RX + int(3 * S), body_top + int(12 * S))
    r_shoulder = (body_cx + BODY_RX - int(3 * S), body_top + int(12 * S))

    # ═══════ PILL BODY ═══════
    # Shadow
    draw.rounded_rectangle([body_cx - BODY_RX + SHADOW_OFF,
                            body_top + SHADOW_OFF,
                            body_cx + BODY_RX + SHADOW_OFF,
                            body_bottom + SHADOW_OFF],
                           radius=BODY_RX, fill=shadow_c)
    # Body fill
    draw.rounded_rectangle([body_cx - BODY_RX, body_top,
                            body_cx + BODY_RX, body_bottom],
                           radius=BODY_RX, fill=BODY_FILL,
                           outline=outline, width=max(3, int(3 * S * 0.5)))
    # ─── Apron — simple triangular bib + tied strings ───
    apron_color = (245, 245, 240)
    apron_outline = (200, 190, 175)
    apron_top = body_top + int(8 * S)
    apron_bottom = body_bottom - int(4 * S)
    apron_hw = BODY_RX - int(8 * S)
    # Bib/front panel
    draw.rounded_rectangle([body_cx - apron_hw, apron_top,
                            body_cx + apron_hw, apron_bottom],
                           radius=int(6 * S), fill=apron_color,
                           outline=apron_outline, width=1)
    # Neck strap lines going up toward shoulders
    strap_w = max(1, int(2 * S * 0.3))
    draw.line([(body_cx - apron_hw + int(3 * S), apron_top),
               (body_cx - int(6 * S), body_top - int(4 * S))],
              fill=apron_outline, width=strap_w)
    draw.line([(body_cx + apron_hw - int(3 * S), apron_top),
               (body_cx + int(6 * S), body_top - int(4 * S))],
              fill=apron_outline, width=strap_w)
    # Waist bow — small horizontal detail
    bow_y = body_cy + int(4 * S)
    bow_r = int(5 * S)
    for bside in [-1, 1]:
        draw.ellipse([body_cx + bside * int(6 * S) - bow_r,
                      bow_y - bow_r // 2,
                      body_cx + bside * int(6 * S) + bow_r,
                      bow_y + bow_r // 2],
                     fill=apron_color, outline=apron_outline, width=1)
    # Bow knot center
    draw.ellipse([body_cx - int(3 * S), bow_y - int(2 * S),
                  body_cx + int(3 * S), bow_y + int(2 * S)],
                 fill=apron_outline)

    # ═══════ LEGS — stick limbs from bottom of pill ═══════
    hip_y = body_bottom - int(5 * S)
    leg_spread = int(12 * S)
    l_hip = (body_cx - leg_spread, hip_y)
    r_hip = (body_cx + leg_spread, hip_y)
    # Simple standing legs going behind counter
    l_foot = (body_cx - int(20 * S), counter_y + int(45 * S))
    r_foot = (body_cx + int(20 * S), counter_y + int(45 * S))
    l_knee = (body_cx - int(15 * S) + int(weight_shift * 0.1),
              int((hip_y + l_foot[1]) / 2))
    r_knee = (body_cx + int(15 * S) + int(weight_shift * 0.1),
              int((hip_y + r_foot[1]) / 2))
    draw_limb_seg(draw, l_hip, l_knee, outline, LW, True, shadow_c)
    draw_limb_seg(draw, l_knee, l_foot, outline, LW, True, shadow_c)
    draw_limb_seg(draw, r_hip, r_knee, outline, LW, True, shadow_c)
    draw_limb_seg(draw, r_knee, r_foot, outline, LW, True, shadow_c)
    # Feet — small ovals
    foot_rx, foot_ry = int(6 * S), int(3 * S)
    for f in [l_foot, r_foot]:
        draw.ellipse([f[0] - foot_rx, f[1] - foot_ry,
                      f[0] + foot_rx + int(3 * S), f[1] + foot_ry],
                     fill=outline)

    # ═══════ HEAD ═══════
    head_cx = body_cx + int(weight_shift * 0.2) + head_tilt_x + int(micro_sway)
    head_cy = int(HEAD_CY_BASE + head_bob - breath)

    # Head shadow
    draw.ellipse([head_cx - HEAD_R + SHADOW_OFF, head_cy - HEAD_R + SHADOW_OFF,
                  head_cx + HEAD_R + SHADOW_OFF, head_cy + HEAD_R + SHADOW_OFF],
                 fill=shadow_c)
    # Head fill
    draw.ellipse([head_cx - HEAD_R, head_cy - HEAD_R,
                  head_cx + HEAD_R, head_cy + HEAD_R],
                 fill=SKIN_COLOR, outline=outline,
                 width=max(3, int(3 * S * 0.5)))

    # Color for brows / blink line (neutral dark tone)
    feat_color = (70, 62, 55)

    # ─── Mouth animation ───
    mouth_phase = t * 18
    mouth_openness = max(0,
        math.sin(mouth_phase) * 0.5 +
        math.sin(mouth_phase * 1.7) * 0.25 +
        math.sin(mouth_phase * 0.6) * 0.15 +
        math.sin(mouth_phase * 2.3) * 0.1)
    is_talking = t < 0.88

    # ─── Eye blink system ───
    blink_cycle = (t * 0.3) % 1.0
    blink_squeeze = 0.0
    if 0.92 < blink_cycle < 0.98:
        bt = (blink_cycle - 0.92) / 0.06
        blink_squeeze = 1.0 - abs(2 * bt - 1)
        blink_squeeze = ease_in_out(blink_squeeze)

    # ─── Eye gaze ───
    eye_off_y = int(6 * S)
    eye_y = head_cy - eye_off_y
    glance_cycle = (t * 0.15) % 1.0
    if 0.7 < glance_cycle < 0.85:
        eye_look_x = 0
        eye_look_y = 0
    else:
        eye_look_x = int(ease_sin(t, freq=0.4) * 3 * S)
        eye_look_y = int(3 * S) if pose in ("chop", "stir") else int(-2 * S)

    eye_sep = int(20 * S)
    eye_r_outer = int(11 * S)
    eye_r_inner = int(6 * S)
    eye_hl_r = int(2.5 * S)

    for sx in [-eye_sep, eye_sep]:
        ex_center = head_cx + sx
        blink_squish = int(eye_r_outer * blink_squeeze * 0.85)
        if blink_squeeze > 0.7:
            draw.line([(ex_center - eye_r_outer, eye_y),
                       (ex_center + eye_r_outer, eye_y)],
                      fill=feat_color, width=max(2, int(2 * S * 0.4)))
        else:
            draw.ellipse([ex_center - eye_r_outer,
                          eye_y - eye_r_outer + blink_squish,
                          ex_center + eye_r_outer,
                          eye_y + eye_r_outer - blink_squish],
                         fill=(255, 255, 255), outline=outline, width=1)
            if blink_squeeze < 0.5:
                draw.ellipse([ex_center - eye_r_inner + eye_look_x,
                              eye_y - eye_r_inner + eye_look_y,
                              ex_center + eye_r_inner + eye_look_x,
                              eye_y + eye_r_inner + eye_look_y],
                             fill=(40, 35, 32))
                draw.ellipse([ex_center - eye_hl_r + eye_look_x + int(2 * S),
                              eye_y - int(3 * S) + eye_look_y,
                              ex_center + eye_hl_r + eye_look_x + int(2 * S),
                              eye_y + eye_look_y],
                             fill=(255, 255, 255))

    # ─── Eyebrows ───
    brow_raise = int(2 * S * mouth_openness) if is_talking else 0
    concern_furrow = int(ease_sin(t, freq=0.3, phase=0.8) * 1.5 * S)
    brow_y = eye_y - int(16 * S) - brow_raise
    brow_half = int(10 * S)
    brow_w = max(2, int(2.5 * S * 0.4))
    draw.line([(head_cx - eye_sep - brow_half, brow_y + int(1 * S) + concern_furrow),
               (head_cx - eye_sep + brow_half, brow_y - int(1 * S) - concern_furrow)],
              fill=feat_color, width=brow_w)
    draw.line([(head_cx + eye_sep - brow_half, brow_y - int(1 * S) - concern_furrow),
               (head_cx + eye_sep + brow_half, brow_y + int(1 * S) + concern_furrow)],
              fill=feat_color, width=brow_w)

    # ─── Mouth ───
    mouth_off = int(18 * S)
    mouth_half = int(14 * S)
    mouth_y = head_cy + mouth_off
    if is_talking and mouth_openness > 0.12:
        mo = int(mouth_openness * 12 * S)
        mouth_width_mod = 0.7 + 0.3 * abs(math.sin(mouth_phase * 0.8))
        mw = int(mouth_half * mouth_width_mod)
        draw.ellipse([head_cx - mw, mouth_y - mo // 2,
                      head_cx + mw, mouth_y + mo // 2 + int(2 * S)],
                     fill=(65, 48, 45))
        if mo > int(8 * S):
            teeth_h = int(2.5 * S)
            draw.rectangle([head_cx - mw + int(3 * S), mouth_y - mo // 2,
                            head_cx + mw - int(3 * S), mouth_y - mo // 2 + teeth_h],
                           fill=(245, 242, 238))
    elif is_talking and mouth_openness > 0.03:
        mo = int(mouth_openness * 5 * S)
        draw.arc([head_cx - mouth_half, mouth_y - int(2 * S),
                  head_cx + mouth_half, mouth_y + int(5 * S) + mo],
                 start=10, end=170, fill=feat_color,
                 width=max(2, int(2 * S * 0.5)))
    else:
        smile_amt = int(ease_sin(t, freq=0.2, phase=0.5) * 1 * S)
        draw.arc([head_cx - mouth_half, mouth_y - int(4 * S) - smile_amt,
                  head_cx + mouth_half, mouth_y + int(7 * S) + smile_amt],
                 start=15, end=165, fill=feat_color,
                 width=max(2, int(2 * S * 0.5)))

    # Blush spots
    blush_r = int(8 * S)
    blush_color = (255, 210, 195, 50)
    for bsx in [-int(28 * S), int(28 * S)]:
        by = head_cy + int(8 * S)
        draw.ellipse([head_cx + bsx - blush_r, by - blush_r // 2,
                      head_cx + bsx + blush_r, by + blush_r // 2],
                     fill=(255, 220, 210))

    # ═══════ ARMS — IK driven, stick limbs ═══════
    hand_r = int(5 * S)

    if pose == "chop":
        board_cx = cx + int(70 * S)
        board_surface = counter_y - int(10 * S)

        kh = chop_curve(t, freq=2.0)
        max_raise = int(120 * S)

        knife_ext = int(30 * S)
        hand_bottom_y = board_surface - int(25 * S)
        hand_top_y = hand_bottom_y - max_raise
        r_hand_y = int(hand_top_y + (1.0 - kh) * (hand_bottom_y - hand_top_y))
        r_hand_x = board_cx + int(6 * S) + int((1 - kh) * 8 * S)
        r_hand = (r_hand_x, r_hand_y)

        r_elbow = ik_arm(r_shoulder, r_hand, UPPER_ARM_LEN, FOREARM_LEN,
                         bend_dir=-1)
        draw_limb_seg(draw, r_shoulder, r_elbow, outline, LW, True, shadow_c)
        draw_limb_seg(draw, r_elbow, r_hand, outline, LW, True, shadow_c)

        # Hand circle
        draw.ellipse([r_hand[0] - hand_r, r_hand[1] - hand_r,
                      r_hand[0] + hand_r, r_hand[1] + hand_r],
                     fill=SKIN_COLOR, outline=outline, width=2)

        # Knife
        fa = math.atan2(r_hand[1] - r_elbow[1], r_hand[0] - r_elbow[0])
        blend = 0.3 + 0.7 * (1 - kh)
        knife_angle = fa * (1 - blend) + (math.pi / 2) * blend
        k_tip_x = r_hand[0] + int(knife_ext * math.cos(knife_angle))
        k_tip_y = r_hand[1] + int(knife_ext * math.sin(knife_angle))
        draw.line([(r_hand[0], r_hand[1] + int(3 * S)),
                   (k_tip_x, k_tip_y)],
                  fill=(185, 190, 195), width=max(2, int(3 * S * 0.4)))
        h_len = int(12 * S)
        h_end_x = r_hand[0] - int(h_len * math.cos(knife_angle))
        h_end_y = r_hand[1] - int(h_len * math.sin(knife_angle))
        draw.line([(r_hand[0], r_hand[1]), (h_end_x, h_end_y)],
                  fill=(140, 115, 80), width=max(3, int(4 * S * 0.4)))

        # Left arm: holding food
        l_hand = (board_cx - int(35 * S) + int(ease_sin(t, 0.3) * 3 * S),
                  board_surface - int(14 * S))
        l_elbow = ik_arm(l_shoulder, l_hand, UPPER_ARM_LEN, FOREARM_LEN,
                         bend_dir=1)
        draw_limb_seg(draw, l_shoulder, l_elbow, outline, LW, True, shadow_c)
        draw_limb_seg(draw, l_elbow, l_hand, outline, LW, True, shadow_c)
        draw.ellipse([l_hand[0] - hand_r, l_hand[1] - hand_r,
                      l_hand[0] + hand_r, l_hand[1] + hand_r],
                     fill=SKIN_COLOR, outline=outline, width=2)

    elif pose == "stir":
        pot_cx = cx + int(80 * S)
        pot_rim_y = counter_y - int(32 * S)

        stir_angle = t * math.pi * 4
        orbit_rx = int(14 * S)
        orbit_ry = int(6 * S)
        r_hand_x = pot_cx + int(orbit_rx * math.cos(stir_angle))
        r_hand_y = pot_rim_y - int(4 * S) + int(orbit_ry * math.sin(stir_angle))
        r_hand = (r_hand_x, r_hand_y)

        r_elbow = ik_arm(r_shoulder, r_hand, UPPER_ARM_LEN, FOREARM_LEN,
                         bend_dir=-1)
        draw_limb_seg(draw, r_shoulder, r_elbow, outline, LW, True, shadow_c)
        draw_limb_seg(draw, r_elbow, r_hand, outline, LW, True, shadow_c)
        draw.ellipse([r_hand[0] - hand_r, r_hand[1] - hand_r,
                      r_hand[0] + hand_r, r_hand[1] + hand_r],
                     fill=SKIN_COLOR, outline=outline, width=2)

        # Spoon
        sp_len = int(16 * S)
        sp_angle = math.pi / 2 + math.atan2(0, pot_cx - r_hand_x) * 0.15
        sp_tip = (r_hand[0] + int(sp_len * math.cos(sp_angle)),
                  r_hand[1] + int(sp_len * math.sin(sp_angle)))
        draw.line([r_hand, sp_tip], fill=(190, 180, 165),
                  width=max(2, int(2.5 * S * 0.4)))
        sp_r = int(4 * S)
        draw.ellipse([sp_tip[0] - sp_r, sp_tip[1] - int(2 * S),
                      sp_tip[0] + sp_r, sp_tip[1] + int(3 * S)],
                     fill=(190, 180, 165), outline=(170, 160, 145), width=1)

        # Left arm resting
        l_hand = (cx - int(50 * S),
                  counter_y - int(8 * S) + int(ease_sin(t, 0.5) * 3 * S))
        l_elbow = ik_arm(l_shoulder, l_hand, UPPER_ARM_LEN, FOREARM_LEN,
                         bend_dir=1)
        draw_limb_seg(draw, l_shoulder, l_elbow, outline, LW, True, shadow_c)
        draw_limb_seg(draw, l_elbow, l_hand, outline, LW, True, shadow_c)
        draw.ellipse([l_hand[0] - hand_r, l_hand[1] - hand_r,
                      l_hand[0] + hand_r, l_hand[1] + hand_r],
                     fill=SKIN_COLOR, outline=outline, width=2)

    elif pose == "mug":
        sway = int(ease_sin(t, freq=0.6) * 4 * S)
        sip_cycle = (t * 0.8) % 1.0
        if 0.15 < sip_cycle < 0.35:
            sip_t = (sip_cycle - 0.15) / 0.20
            sip_raise = int(ease_in_out(sip_t) * 40 * S)
        elif 0.35 <= sip_cycle < 0.55:
            sip_t = (sip_cycle - 0.35) / 0.20
            sip_raise = int((1 - ease_in_out(sip_t)) * 40 * S)
        else:
            sip_raise = 0

        mug_cx = cx + int(20 * S) + sway
        mug_cy = int(body_top + 60 * S + breath * 0.3 - sip_raise)

        r_hand = (mug_cx + int(14 * S), mug_cy)
        r_elbow = ik_arm(r_shoulder, r_hand, UPPER_ARM_LEN, FOREARM_LEN,
                         bend_dir=-1)
        draw_limb_seg(draw, r_shoulder, r_elbow, outline, LW, True, shadow_c)
        draw_limb_seg(draw, r_elbow, r_hand, outline, LW, True, shadow_c)

        l_hand = (mug_cx - int(14 * S), mug_cy + int(3 * S))
        l_elbow = ik_arm(l_shoulder, l_hand, UPPER_ARM_LEN, FOREARM_LEN,
                         bend_dir=1)
        draw_limb_seg(draw, l_shoulder, l_elbow, outline, LW, True, shadow_c)
        draw_limb_seg(draw, l_elbow, l_hand, outline, LW, True, shadow_c)

        # Hand circles
        for h in [r_hand, l_hand]:
            draw.ellipse([h[0] - hand_r, h[1] - hand_r,
                          h[0] + hand_r, h[1] + hand_r],
                         fill=SKIN_COLOR, outline=outline, width=2)

        # Mug
        mug_hw = int(16 * S)
        mug_ht = int(10 * S)
        mug_hb = int(24 * S)
        draw.rounded_rectangle([mug_cx - mug_hw, mug_cy - mug_ht,
                                mug_cx + mug_hw, mug_cy + mug_hb],
                               radius=int(4 * S), fill=(255, 250, 240),
                               outline=outline,
                               width=max(2, int(2.5 * S * 0.4)))
        # Handle
        arc_x1 = mug_cx + int(14 * S)
        arc_x2 = mug_cx + int(28 * S)
        draw.arc([arc_x1, mug_cy - int(4 * S), arc_x2, mug_cy + int(16 * S)],
                 start=270, end=90, fill=outline,
                 width=max(2, int(2.5 * S * 0.4)))

        # Steam wisps
        steam_sp = int(6 * S)
        for i in range(3):
            sx = mug_cx - steam_sp + i * steam_sp
            for step in range(5):
                sy1 = mug_cy - int(16 * S) - step * int(14 * S)
                sy2 = sy1 - int(14 * S)
                sx_off = int(8 * S * ease_sin(t, freq=1.5 + i * 0.3,
                                              phase=step * 0.8 + i))
                fade = max(0.0, 1.0 - step * 0.2)
                sc = tuple(int(200 * fade + 30 * (1 - fade)) for _ in range(3))
                draw.line([(sx + sx_off, sy1), (sx + sx_off + int(2 * S), sy2)],
                          fill=sc, width=max(1, int(2 * S * 0.5)))


def draw_counter_props(draw, cx, counter_y, prop_type, t):
    """Draw cartoon-style counter props matching chibi aesthetic."""
    outline = OUTLINE_COLOR
    ol_w = max(2, int(2.5 * S * 0.4))

    if prop_type == "pot":
        pot_cx = cx + int(80 * S)
        pot_y = counter_y
        pw, ph = int(60 * S), int(40 * S)

        # Pot body — rounded cartoon shape
        draw.rounded_rectangle([pot_cx - pw // 2, pot_y - ph,
                                pot_cx + pw // 2, pot_y + 2],
                               radius=int(8 * S),
                               fill=(180, 185, 195),
                               outline=outline, width=ol_w)
        # Rim
        rim_h = int(5 * S)
        draw.rounded_rectangle([pot_cx - pw // 2 - int(4 * S),
                                pot_y - ph - rim_h,
                                pot_cx + pw // 2 + int(4 * S),
                                pot_y - ph + int(2 * S)],
                               radius=int(3 * S),
                               fill=(200, 205, 215),
                               outline=outline, width=ol_w)
        # Handles — simple rounded stubs
        handle_w = int(12 * S)
        for side in [-1, 1]:
            hx = pot_cx + side * (pw // 2 + int(2 * S))
            hy = pot_y - ph // 2
            draw.rounded_rectangle([hx - (handle_w if side < 0 else 0),
                                    hy - int(4 * S),
                                    hx + (0 if side < 0 else handle_w),
                                    hy + int(4 * S)],
                                   radius=int(3 * S),
                                   fill=(200, 205, 215),
                                   outline=outline, width=ol_w)
        # Soup/stew fill visible
        draw.rounded_rectangle([pot_cx - pw // 2 + int(6 * S),
                                pot_y - ph + int(3 * S),
                                pot_cx + pw // 2 - int(6 * S),
                                pot_y - ph + int(12 * S)],
                               radius=int(3 * S), fill=(140, 100, 60))

        # Steam wisps
        steam_sp = int(10 * S)
        for i in range(4):
            sx = pot_cx - int(15 * S) + i * steam_sp
            for step in range(5):
                sy1 = pot_y - ph - int(10 * S) - step * int(12 * S)
                sy2 = sy1 - int(12 * S)
                sx_off = int(8 * S * ease_sin(t, freq=1.2 + i * 0.2,
                                              phase=step * 0.7 + i * 1.3))
                fade = max(0.0, 1.0 - step * 0.2)
                sc = tuple(int(200 * fade + 60 * (1 - fade)) for _ in range(3))
                draw.line([(sx + sx_off, sy1),
                           (sx + sx_off + int(2 * S), sy2)],
                          fill=sc, width=max(1, int(2 * S * 0.4)))

    elif prop_type == "board":
        board_cx = cx + int(70 * S)
        board_top = counter_y - int(10 * S)
        bw, bh = int(90 * S), int(14 * S)

        # Cutting board — cartoon rounded rectangle
        draw.rounded_rectangle([board_cx - bw // 2, board_top,
                                board_cx + bw // 2, board_top + bh],
                               radius=int(5 * S),
                               fill=(210, 180, 130),
                               outline=outline, width=ol_w)
        # Simple wood grain lines
        grain_sp = max(3, int(4 * S))
        for gy in range(board_top + int(3 * S),
                        board_top + bh - int(2 * S), grain_sp):
            draw.line([(board_cx - bw // 2 + int(6 * S), gy),
                       (board_cx + bw // 2 - int(6 * S), gy)],
                      fill=(195, 165, 115), width=1)

        kh = chop_curve(t, freq=2.0)
        knife_down = 1.0 - kh
        veg_colors = [(100, 190, 100), (230, 90, 70),
                      (255, 200, 60), (100, 190, 100)]
        veg_h = int(10 * S)
        veg_w = int(9 * S)

        # Uncut veggies left side
        for i, vx_base in enumerate([-30, -20, -10]):
            vc = veg_colors[i]
            vx = int(vx_base * S)
            draw.rounded_rectangle([board_cx + vx, board_top - veg_h + 2,
                                    board_cx + vx + veg_w, board_top + 2],
                                   radius=int(2 * S), fill=vc,
                                   outline=outline, width=1)

        # Active cut veggie with spread
        cut_spread = int(knife_down * 4 * S)
        cut_veg_x = board_cx + int(4 * S)
        cvw = int(5 * S)
        for sign, off in [(-1, -cut_spread), (1, cut_spread)]:
            draw.rounded_rectangle([cut_veg_x + off + (0 if sign > 0 else -cvw),
                                    board_top - veg_h + 2,
                                    cut_veg_x + off + (cvw if sign > 0 else 0),
                                    board_top + 2],
                                   radius=max(1, int(S)), fill=(230, 90, 70),
                                   outline=outline, width=1)

        # Cut pieces on right
        for i, vx_base in enumerate([18, 26, 34, 40]):
            vc = veg_colors[i % len(veg_colors)]
            vx = int(vx_base * S)
            dy = int(ease_sin(t, freq=0.3, phase=i) * 1.5 * S)
            draw.rounded_rectangle([board_cx + vx,
                                    board_top - veg_h // 2 + dy,
                                    board_cx + vx + int(7 * S),
                                    board_top + 2 + dy],
                                   radius=max(1, int(S)), fill=vc,
                                   outline=outline, width=1)


def draw_top_captions(img, lines, highlight_word=None, fade_alpha=1.0):
    """Draw clean captions at the top of the screen — no box.
    Text with a subtle dark shadow for readability on the kitchen photo.
    Returns modified PIL Image.
    """
    if not lines or fade_alpha <= 0:
        return img

    draw = ImageDraw.Draw(img)
    font = load_font(FONT_BOLD, 48)
    text_color = (255, 252, 245)
    shadow_color = (15, 12, 10)
    hl_color = AMBER_GLOW

    # Measure lines
    line_data = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        line_data.append((line, tw, th))

    line_spacing = 16
    total_h = sum(ld[2] for ld in line_data) + line_spacing * (len(line_data) - 1)
    # Start in the middle of the top area
    text_y = 300

    for line_text, tw, th in line_data:
        x = (W - tw) // 2

        # Shadow pass (offset 2px down-right for depth)
        for sx, sy in [(2, 2), (-1, 2), (2, -1), (0, 3)]:
            draw.text((x + sx, text_y + sy), line_text,
                      fill=shadow_color, font=font)

        if highlight_word and highlight_word.lower() in line_text.lower():
            idx = line_text.lower().index(highlight_word.lower())
            before = line_text[:idx]
            hl = line_text[idx:idx + len(highlight_word)]
            draw.text((x, text_y), line_text, fill=text_color, font=font)
            if before:
                bw = draw.textbbox((0, 0), before, font=font)[2]
            else:
                bw = 0
            draw.text((x + bw, text_y), hl, fill=hl_color, font=font)
        else:
            draw.text((x, text_y), line_text, fill=text_color, font=font)

        text_y += th + line_spacing

    return img


def draw_counter_surface(draw, counter_y):
    """Draw a cartoon-style counter surface matching the chibi kitchen."""
    outline = OUTLINE_COLOR
    ol_w = max(2, int(2.5 * S * 0.4))
    # Counter top surface — warm wood color with rounded edge feel
    draw.rectangle([(0, counter_y), (W, counter_y + 6)],
                   fill=(175, 145, 110))
    # Counter front face
    draw.rectangle([(0, counter_y + 6), (W, counter_y + COUNTER_HEIGHT)],
                   fill=(140, 115, 85))
    # Panel detail lines (cartoon cabinet fronts below counter)
    panel_w = int(100 * S)
    panel_margin = int(10 * S)
    panel_top = counter_y + 14
    panel_bottom = counter_y + COUNTER_HEIGHT - 6
    for px in range(panel_margin, W - panel_margin, panel_w + panel_margin):
        draw.rounded_rectangle([px, panel_top,
                                min(px + panel_w, W - panel_margin),
                                panel_bottom],
                               radius=int(3 * S), outline=(120, 98, 70),
                               width=1)
    # Top highlight
    draw.line([(0, counter_y), (W, counter_y)],
              fill=(200, 175, 145), width=2)
    # Bottom edge
    draw.line([(0, counter_y + COUNTER_HEIGHT),
               (W, counter_y + COUNTER_HEIGHT)],
              fill=outline, width=2)


def render_stick_frame(slide_idx, t, caption_lines=None, highlight_word=None):
    """Render one frame: figure behind counter, captions at top.
    slide_idx: 0=stir, 1=chop, 2=mug. t: 0-1 progress.
    Returns numpy RGB array.
    """
    # Seed wobble per-frame so hand-drawn lines are consistent within
    # a frame but shift slightly between frames (animated pencil feel).
    # Use slide + progress to get a slowly-changing seed.
    np.random.seed(int(slide_idx * 10000 + t * 300) % (2**31))
    
    bg = get_kitchen_bg().copy()
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img)

    cx = FIGURE_CX

    # Draw figure FIRST (behind counter)
    if slide_idx == 0:
        draw_fluid_figure(draw, cx, "stir", t, COUNTER_Y)
    elif slide_idx == 1:
        draw_fluid_figure(draw, cx, "chop", t, COUNTER_Y)
    elif slide_idx == 2:
        draw_fluid_figure(draw, cx + int(30 * S), "mug", t, COUNTER_Y)

    # Draw counter ON TOP of figure — hides legs/hips
    draw_counter_surface(draw, COUNTER_Y)

    # Props sit ON the counter (drawn after counter surface)
    if slide_idx == 0:
        draw_counter_props(draw, cx, COUNTER_Y, "pot", t)
    elif slide_idx == 1:
        draw_counter_props(draw, cx, COUNTER_Y, "board", t)

    # Captions at the top — no box, just clean text with shadow
    if caption_lines:
        fade = min(1.0, t / 0.18) if t < 0.18 else 1.0
        img = draw_top_captions(img, caption_lines, highlight_word, fade_alpha=fade)

    arr = np.array(img)
    arr = apply_paper_texture(arr, opacity=0.10)
    arr = apply_grain(arr, amount=4)
    arr = apply_vignette(arr, strength=0.25)
    return arr


# Captions for the three stick-figure slides — matches VO script
STICK_CAPTIONS = [
    {
        "lines": [
            "Someone you love is struggling,",
            "and you have no idea",
            "what to say.",
        ],
        "highlight": "what to say.",
    },
    {
        "lines": [
            "You're not scared of saying",
            "the wrong thing.",
            "You're scared of saying nothing.",
        ],
        "highlight": "nothing.",
    },
    {
        "lines": [
            "So you just... don't bring it up.",
            "And that silence?",
            "It stays with you.",
        ],
        "highlight": "stays with you.",
    },
]


def blend_frames(frame_a, frame_b, alpha):
    """Blend two RGB numpy arrays. alpha=0 -> all A, alpha=1 -> all B."""
    return (frame_a * (1 - alpha) + frame_b * alpha).astype(np.uint8)


def composite_watermark(frame, watermark_rgba):
    """Composite RGBA watermark onto RGB frame."""
    wm = np.array(watermark_rgba)
    alpha = wm[:, :, 3:4].astype(float) / 255.0
    rgb = wm[:, :, :3].astype(float)
    base = frame.astype(float)
    result = base * (1 - alpha) + rgb * alpha
    return result.astype(np.uint8)


def build_v3():
    print("Building Ask Anyway Campaign v3 (frame-by-frame)...")

    # Load VO manifest
    manifest = json.loads((VO_DIR / "manifest.json").read_text())

    # Slide definitions — each slide gets a warm gradient background
    pads = [0.5, 0.3, 0.3, 0.3, 0.5, 1.0]
    slide_defs = [
        {
            "bg": WARM_BLACK, "gradient": (WARM_BLACK, WARM_BLACK_2),
            "lines": ["Someone you love", "is struggling,", "", "and you have", "no idea", "what to say."],
            "color": WARM_WHITE, "font": FONT_BLACK, "size": 64,
            "highlight": "what to say.", "fade_dur": 0.2,
        },
        {
            "bg": CREAM, "gradient": (CREAM, CREAM_2),
            "lines": ["You're not scared", "of saying the", "wrong thing.", "",
                      "You're scared", "of saying nothing."],
            "color": CHARCOAL, "font": FONT_BOLD, "size": 68,
            "highlight": "nothing.", "hl_color": TEAL, "fade_dur": 0.35,
        },
        {
            "bg": TEAL_DARK, "gradient": (TEAL_DARK, TEAL_MID),
            "lines": ["So you just...", "don't bring it up.", "",
                      "And that silence?", "It stays with you."],
            "color": WARM_WHITE, "font": FONT_BOLD, "size": 64,
            "highlight": "stays with you.", "fade_dur": 0.4,
        },
        {
            "bg": TEAL, "gradient": (TEAL_MID, TEAL),
            "lines": ["We built a guide", "with a real therapist.", "",
                      "Real words you can", "actually use."],
            "color": WARM_WHITE, "font": FONT_BLACK, "size": 72,
            "fade_dur": 0.25,
        },
        {
            "bg": WARM_BLACK, "gradient": (WARM_BLACK_2, WARM_BLACK),
            "lines": ["The conversation", "doesn't have to", "be perfect.", "",
                      "It just has to", "happen."],
            "color": WARM_WHITE, "font": FONT_BLACK, "size": 72,
            "highlight": "happen.", "fade_dur": 0.3,
            "subtitle": "Clinically informed. Personally driven.",
        },
        {
            "bg": CREAM, "gradient": (CREAM, CREAM_2), "cta_slide": True, "fade_dur": 0.35,
        },
    ]

    # Pre-render all slide images
    slide_images = []
    bg_images = []
    for sd in slide_defs:
        # Background for fade-in: gradient or flat
        if sd.get("gradient"):
            bg = render_gradient(sd["gradient"][0], sd["gradient"][1])
            bg_arr = apply_grain(np.array(bg), amount=6)
            bg_arr = apply_vignette(bg_arr, strength=0.35)
        else:
            bg = Image.new("RGB", (W, H), sd["bg"])
            bg_arr = np.array(bg)
        bg_images.append(bg_arr)

        if sd.get("cta_slide"):
            cta = render_gradient(sd["gradient"][0], sd["gradient"][1]) if sd.get("gradient") else Image.new("RGB", (W, H), sd["bg"])
            cta = draw_cta_logo(cta)
            cta_arr = apply_grain(np.array(cta), amount=6)
            cta_arr = apply_vignette(cta_arr, strength=0.25)
            slide_images.append(cta_arr)
        else:
            txt_img = render_text_image(
                sd["bg"], sd["lines"], sd["color"], sd["font"], sd["size"],
                highlight_word=sd.get("highlight"),
                highlight_color=sd.get("hl_color", AMBER),
                subtitle=sd.get("subtitle"),
                gradient=sd.get("gradient"),
            )
            slide_images.append(np.array(txt_img))

    # Calculate durations
    # Slides 0-2: VO-driven (stick figure). Slides 3-5: fixed (text cards, no VO)
    end_slide_durations = [4.2, 4.2, 4.8]   # extra read time on final three slides
    durations = []
    for i, pad in enumerate(pads):
        if str(i + 1) in manifest:
            durations.append(manifest[str(i + 1)]["duration"] + pad)
        else:
            end_idx = i - 3
            durations.append(end_slide_durations[end_idx])

    total_dur = sum(durations)
    total_frames = int(total_dur * FPS)
    xfade_dur = 0.0  # hard cuts (crossfade disabled to prevent flashing)
    xfade_frames = int(xfade_dur * FPS)

    print(f"  {len(slide_defs)} slides, {total_dur:.1f}s, {total_frames} frames")

    # Pre-render watermark at various opacities
    # Watermark builds from 10% to 45% opacity over the video
    # Skip watermark on last slide (has full logo)
    print("  Pre-rendering watermarks...")
    watermark_cache = {}
    for opacity_pct in range(10, 46):
        op = opacity_pct / 100.0
        watermark_cache[opacity_pct] = np.array(render_logo_watermark(op))

    # Start ffmpeg process
    ffmpeg = get_ffmpeg_exe()
    silent_path = str(OUTPUT_DIR / "v3_silent.mp4")

    cmd = [
        ffmpeg, "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}",
        "-r", str(FPS),
        "-i", "pipe:0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "23",
        silent_path,
    ]

    print("  Rendering frames to ffmpeg...")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    # Generate frames
    frame_num = 0
    slide_start_frames = []
    cumulative = 0
    for d in durations:
        slide_start_frames.append(int(cumulative * FPS))
        cumulative += d

    for frame_idx in range(total_frames):
        t = frame_idx / FPS
        progress_total = frame_idx / total_frames  # 0 to 1 over whole video

        # Determine current slide
        current_slide = 0
        slide_t = t
        for i, d in enumerate(durations):
            if slide_t < d:
                current_slide = i
                break
            slide_t -= d
        else:
            current_slide = len(durations) - 1
            slide_t = durations[-1]

        slide_progress = slide_t / durations[current_slide]
        fade_dur = slide_defs[current_slide]["fade_dur"]
        fade_frames = int(fade_dur * FPS)

        # Slides 0-2: animated stick-figure frames (rendered per frame)
        if current_slide <= 2:
            cap = STICK_CAPTIONS[current_slide]
            frame = render_stick_frame(
                current_slide, slide_progress,
                cap["lines"], highlight_word=cap.get("highlight"),
            )
            # Caption fade-in at start of slide
            frame_in_slide = frame_idx - slide_start_frames[current_slide]
            if current_slide == 0 and frame_in_slide < fade_frames:
                alpha = frame_in_slide / fade_frames
                # Render a no-caption version for fade
                bg_frame = render_stick_frame(current_slide, slide_progress, [], None)
                frame = blend_frames(bg_frame, frame, alpha)

            # Cross-dissolve at boundary (to next slide)
            if current_slide < len(durations) - 1:
                next_slide_start = slide_start_frames[current_slide + 1]
                frames_to_next = next_slide_start - frame_idx
                if 0 < frames_to_next <= xfade_frames:
                    xfade_alpha = 1.0 - (frames_to_next / xfade_frames)
                    if current_slide + 1 <= 2:
                        next_cap = STICK_CAPTIONS[current_slide + 1]
                        next_frame = render_stick_frame(
                            current_slide + 1,
                            0,
                            next_cap["lines"],
                            highlight_word=next_cap.get("highlight"),
                        )
                    else:
                        next_frame = apply_zoom(slide_images[current_slide + 1], 0, max_zoom=0.03)
                    frame = blend_frames(frame, next_frame, xfade_alpha)

        else:
            # Slides 3-5: branded cards (pre-rendered static)
            frame = apply_zoom(slide_images[current_slide], slide_progress, max_zoom=0.03)

            # Text fade-in: blend with background at start of slide
            frame_in_slide = frame_idx - slide_start_frames[current_slide]
            if current_slide == 0 and frame_in_slide < fade_frames:
                alpha = frame_in_slide / fade_frames
                bg_zoomed = apply_zoom(bg_images[current_slide], slide_progress, max_zoom=0.03)
                frame = blend_frames(bg_zoomed, frame, alpha)

            # Cross-dissolve at slide boundary
            if current_slide < len(durations) - 1:
                next_slide_start = slide_start_frames[current_slide + 1]
                frames_to_next = next_slide_start - frame_idx
                if 0 < frames_to_next <= xfade_frames:
                    xfade_alpha = 1.0 - (frames_to_next / xfade_frames)
                    next_frame = apply_zoom(slide_images[current_slide + 1], 0, max_zoom=0.03)
                    frame = blend_frames(frame, next_frame, xfade_alpha)

        # Logo watermark (builds 10% -> 45% over video, not on last slide)
        if current_slide < len(durations) - 1:
            wm_opacity_pct = 10 + int(progress_total * 35)
            wm_opacity_pct = max(10, min(45, wm_opacity_pct))
            if wm_opacity_pct in watermark_cache:
                frame = composite_watermark(frame, watermark_cache[wm_opacity_pct])

        # Write frame
        proc.stdin.write(frame.tobytes())

        if frame_idx % 100 == 0:
            pct = frame_idx / total_frames * 100
            sys.stdout.write(f"\r  Frame {frame_idx}/{total_frames} ({pct:.0f}%)")
            sys.stdout.flush()

    proc.stdin.close()
    proc.wait()
    stderr = proc.stderr.read().decode()

    if proc.returncode != 0:
        print(f"\nffmpeg error: {stderr[-500:]}")
        return

    size = os.path.getsize(silent_path)
    print(f"\n  Silent video: {size / 1024:.0f} KB, {total_dur:.1f}s")

    # Now merge audio: VO clips + ambient pad
    # Strategy: create a single VO track first, then overlay on ambient.
    # This avoids amix volume normalization killing the levels.
    print("  Merging audio...")
    ambient_path = str(OUTPUT_DIR / "ambient_pad.wav")
    final_path = str(OUTPUT_DIR / "ask-anyway-v3.mp4")

    # Build ffmpeg audio filter
    audio_inputs = ["-i", silent_path, "-i", ambient_path]
    filter_parts = []

    # Ambient: trim to video length, boost volume
    filter_parts.append(
        f"[1]atrim=0:{total_dur + 1},asetpts=PTS-STARTPTS,volume=1.5[amb]"
    )

    # Add VO inputs — only slides 1-3 have voiceover (stick figure slides)
    vo_count = len(manifest)
    for i in range(1, vo_count + 1):
        vo_file = str(VO_DIR / f"slide-{i:02d}.mp3")
        audio_inputs.extend(["-i", vo_file])
        delay_ms = int(sum(durations[:i - 1]) * 1000)
        input_idx = i + 1
        filter_parts.append(
            f"[{input_idx}]adelay={delay_ms}|{delay_ms},volume=4.0,"
            f"apad=whole_dur={total_dur + 1}[v{i}]"
        )

    # Mix VO clips into one track
    vo_labels = "".join(f"[v{j}]" for j in range(1, vo_count + 1))
    filter_parts.append(
        f"{vo_labels}amix=inputs={vo_count}:duration=first:dropout_transition=0:normalize=0[vo_mix]"
    )

    # Overlay VO mix on ambient — no normalization so volumes stay as set
    filter_parts.append(
        "[amb][vo_mix]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]"
    )

    audio_cmd = [
        ffmpeg, "-y",
        *audio_inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-t", str(total_dur),
        final_path,
    ]

    result = subprocess.run(audio_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Audio merge failed: {result.stderr[-600:]}")
        return

    final_size = os.path.getsize(final_path)
    print(f"  Final: {final_path}")
    print(f"  Size: {final_size / 1024:.0f} KB, Duration: {total_dur:.1f}s")

    # Open it
    subprocess.run(["open", final_path])
    print("  Done!")


if __name__ == "__main__":
    build_v3()
