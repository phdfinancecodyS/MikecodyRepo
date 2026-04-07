#!/usr/bin/env python3
"""
Style Sampler  - renders the same stick figure pose in 8 different visual styles
on a single comparison sheet so the user can pick what feels right.

Output: /tmp/stick-figure-styles.png (4x2 grid, each cell labeled)
"""
import math
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "assets" / "fonts"

def load_font(path, size):
    try:
        return ImageFont.truetype(str(path), size)
    except (OSError, IOError):
        return ImageFont.load_default()

FONT_BOLD = load_font(FONTS_DIR / "Montserrat-Bold.ttf", 28)
FONT_LABEL = load_font(FONTS_DIR / "Montserrat-Bold.ttf", 22)
FONT_DESC = load_font(FONTS_DIR / "Montserrat-Regular.ttf", 16)

# Cell size for each style panel
CW, CH = 540, 700
COLS, ROWS = 4, 2
SHEET_W = CW * COLS
SHEET_H = CH * ROWS + 80  # extra for title

# Common figure proportions (relative to cell)
def fig_dims(scale=1.0):
    return {
        "head_r": int(32 * scale),
        "torso": int(120 * scale),
        "upper_arm": int(55 * scale),
        "forearm": int(48 * scale),
        "upper_leg": int(65 * scale),
        "lower_leg": int(60 * scale),
        "shoulder_spread": int(28 * scale),
    }

def ik_arm(shoulder, hand, upper_len, fore_len, bend_dir=1):
    dx = hand[0] - shoulder[0]
    dy = hand[1] - shoulder[1]
    dist = math.sqrt(dx*dx + dy*dy)
    dist = min(dist, upper_len + fore_len - 1)
    angle_to_hand = math.atan2(dy, dx)
    cos_elbow = (upper_len**2 + dist**2 - fore_len**2) / (2 * upper_len * dist + 1e-6)
    cos_elbow = max(-1, min(1, cos_elbow))
    elbow_offset = math.acos(cos_elbow) * bend_dir
    elbow_angle = angle_to_hand + elbow_offset
    ex = shoulder[0] + int(upper_len * math.cos(elbow_angle))
    ey = shoulder[1] + int(upper_len * math.sin(elbow_angle))
    return (ex, ey)


def draw_common_figure(draw, cx, cy, d, lw, color, head_fill, draw_face_fn,
                        line_fn=None, joint_fn=None):
    """Draw a stick figure in a standard pose (slight lean, one hand raised as if chopping).
    Uses callbacks for style-specific line drawing and face rendering."""
    if line_fn is None:
        line_fn = lambda p1, p2, c, w: draw.line([p1, p2], fill=c, width=w)

    head_cx = cx
    head_cy = cy - d["torso"] - d["head_r"] - 8
    neck = (head_cx, head_cy + d["head_r"])
    mid_sh = (cx, cy - d["torso"])
    l_sh = (cx - d["shoulder_spread"], cy - d["torso"])
    r_sh = (cx + d["shoulder_spread"], cy - d["torso"])
    hip = (cx, cy)

    # Right hand up (chopping motion)
    r_hand = (cx + d["shoulder_spread"] + 35, cy - d["torso"] - 30)
    r_elbow = ik_arm(r_sh, r_hand, d["upper_arm"], d["forearm"], bend_dir=-1)

    # Left hand resting on counter level
    l_hand = (cx - d["shoulder_spread"] - 25, cy - 15)
    l_elbow = ik_arm(l_sh, l_hand, d["upper_arm"], d["forearm"], bend_dir=1)

    # Legs
    l_foot = (cx - 22, cy + d["upper_leg"] + d["lower_leg"])
    r_foot = (cx + 22, cy + d["upper_leg"] + d["lower_leg"])
    l_knee = (cx - 10, cy + d["upper_leg"])
    r_knee = (cx + 10, cy + d["upper_leg"])

    # Draw order: legs, torso, arms, head
    # Legs
    line_fn(hip, l_knee, color, lw)
    line_fn(l_knee, l_foot, color, lw)
    line_fn(hip, r_knee, color, lw)
    line_fn(r_knee, r_foot, color, lw)

    # Torso
    line_fn(neck, mid_sh, color, lw)
    line_fn(l_sh, r_sh, color, lw)
    line_fn(mid_sh, hip, color, lw)

    # Arms
    line_fn(l_sh, l_elbow, color, lw)
    line_fn(l_elbow, l_hand, color, lw)
    line_fn(r_sh, r_elbow, color, lw)
    line_fn(r_elbow, r_hand, color, lw)

    # Joints (optional)
    if joint_fn:
        for pt in [l_sh, r_sh, l_elbow, r_elbow, l_knee, r_knee, hip]:
            joint_fn(pt)

    # Head
    draw.ellipse([head_cx - d["head_r"], head_cy - d["head_r"],
                  head_cx + d["head_r"], head_cy + d["head_r"]],
                 fill=head_fill, outline=color, width=max(2, lw // 2))

    # Face
    draw_face_fn(draw, head_cx, head_cy, d["head_r"], color)

    # Knife in right hand
    knife_len = 28
    k_angle = math.pi / 2 + 0.3
    kx = r_hand[0] + int(knife_len * math.cos(k_angle))
    ky = r_hand[1] + int(knife_len * math.sin(k_angle))
    line_fn(r_hand, (kx, ky), (180, 185, 190), max(2, lw // 2))


def simple_face(draw, cx, cy, r, color):
    """Simple dot eyes + arc mouth."""
    er = max(2, r // 8)
    sep = r // 3
    for sx in [-sep, sep]:
        draw.ellipse([cx + sx - er, cy - er - r//6,
                      cx + sx + er, cy + er - r//6], fill=color)
    mw = r // 2
    draw.arc([cx - mw, cy, cx + mw, cy + r // 3],
             start=15, end=165, fill=color, width=2)


def expressive_face(draw, cx, cy, r, color):
    """Larger eyes with whites, pupils, eyebrows."""
    eye_r = max(3, r // 5)
    pupil_r = max(2, r // 8)
    sep = r // 3
    for sx in [-sep, sep]:
        ex = cx + sx
        ey = cy - r // 6
        draw.ellipse([ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r],
                     fill=(255, 255, 255))
        draw.ellipse([ex - pupil_r + 1, ey - pupil_r,
                      ex + pupil_r + 1, ey + pupil_r], fill=color)
        # Highlight
        hl = max(1, pupil_r // 2)
        draw.ellipse([ex + 1, ey - pupil_r + 1, ex + hl + 1, ey - pupil_r + hl + 1],
                     fill=(255, 255, 255))
        # Eyebrow
        bw = eye_r + 2
        draw.line([(ex - bw, ey - eye_r - 4), (ex + bw, ey - eye_r - 6)],
                  fill=color, width=2)
    # Slight smile
    mw = r // 2
    draw.arc([cx - mw, cy + 2, cx + mw, cy + r // 3 + 2],
             start=10, end=170, fill=color, width=2)


def wobble_line(draw, p1, p2, color, width, segments=6):
    """Hand-drawn wobbly line between two points."""
    pts = [p1]
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    seg_len = math.sqrt(dx*dx + dy*dy)
    if seg_len < 1:
        return
    nx, ny = -dy / seg_len, dx / seg_len  # normal
    for i in range(1, segments):
        t = i / segments
        mx = p1[0] + dx * t + nx * np.random.normal(0, seg_len * 0.02)
        my = p1[1] + dy * t + ny * np.random.normal(0, seg_len * 0.02)
        pts.append((int(mx), int(my)))
    pts.append(p2)
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=color, width=width)


def heavy_wobble_line(draw, p1, p2, color, width, segments=8):
    """More dramatically wobbly line."""
    pts = [p1]
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    seg_len = math.sqrt(dx*dx + dy*dy)
    if seg_len < 1:
        return
    nx, ny = -dy / seg_len, dx / seg_len
    for i in range(1, segments):
        t = i / segments
        mx = p1[0] + dx * t + nx * np.random.normal(0, seg_len * 0.045)
        my = p1[1] + dy * t + ny * np.random.normal(0, seg_len * 0.045)
        pts.append((int(mx), int(my)))
    pts.append(p2)
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=color, width=width)


# ═══════════════════════════════════════════════════════════════
# STYLE 1: Current style  - warm figure on photo, skin fill, detailed face
# ═══════════════════════════════════════════════════════════════
def render_style_current(cell):
    draw = ImageDraw.Draw(cell)
    # Simulate kitchen bg
    for y in range(CH):
        t = y / CH
        c = int(35 + t * 20)
        draw.line([(0, y), (CW, y)], fill=(c, c - 3, c - 6))

    np.random.seed(1)
    d = fig_dims(1.0)
    cx, cy = CW // 2, CH // 2 + 40

    def face_fn(dr, hcx, hcy, hr, col):
        expressive_face(dr, hcx, hcy, hr, (80, 70, 60))

    def line_fn(p1, p2, c, w):
        wobble_line(draw, p1, p2, c, w)

    draw_common_figure(draw, cx, cy, d, 5, (240, 235, 225), (250, 245, 238),
                       face_fn, line_fn)


# ═══════════════════════════════════════════════════════════════
# STYLE 2: Classic minimal  - thin black on white, XKCD-like
# ═══════════════════════════════════════════════════════════════
def render_style_minimal(cell):
    draw = ImageDraw.Draw(cell)
    draw.rectangle([0, 0, CW, CH], fill=(255, 255, 255))
    d = fig_dims(1.0)
    cx, cy = CW // 2, CH // 2 + 40
    color = (30, 30, 30)

    def face_fn(dr, hcx, hcy, hr, col):
        simple_face(dr, hcx, hcy, hr, col)

    draw_common_figure(draw, cx, cy, d, 3, color, (255, 255, 255), face_fn)


# ═══════════════════════════════════════════════════════════════
# STYLE 3: Whiteboard / chalkboard  - white on dark, sketchy lines
# ═══════════════════════════════════════════════════════════════
def render_style_whiteboard(cell):
    draw = ImageDraw.Draw(cell)
    # Dark green chalkboard
    for y in range(CH):
        t = y / CH
        g = int(42 + t * 8)
        draw.line([(0, y), (CW, y)], fill=(30, g, 35))
    # Chalk dust texture
    for _ in range(800):
        x = np.random.randint(0, CW)
        y = np.random.randint(0, CH)
        a = np.random.randint(15, 40)
        draw.point((x, y), fill=(a + 180, a + 180, a + 170))

    np.random.seed(2)
    d = fig_dims(1.0)
    cx, cy = CW // 2, CH // 2 + 40
    chalk = (235, 232, 220)

    def face_fn(dr, hcx, hcy, hr, col):
        simple_face(dr, hcx, hcy, hr, chalk)

    def line_fn(p1, p2, c, w):
        heavy_wobble_line(draw, p1, p2, c, w)

    draw_common_figure(draw, cx, cy, d, 4, chalk, (45, 58, 48), face_fn, line_fn)


# ═══════════════════════════════════════════════════════════════
# STYLE 4: Bold cartoon  - thick outlines, color fills, TheOdd1sOut-like
# ═══════════════════════════════════════════════════════════════
def render_style_bold_cartoon(cell):
    draw = ImageDraw.Draw(cell)
    # Soft warm background
    for y in range(CH):
        t = y / CH
        r = int(255 - t * 15)
        g = int(248 - t * 18)
        b = int(235 - t * 20)
        draw.line([(0, y), (CW, y)], fill=(r, g, b))

    d = fig_dims(1.15)
    cx, cy = CW // 2, CH // 2 + 30
    outline = (45, 40, 35)
    body_fill = (255, 220, 185)  # warm skin tone
    head_fill = (255, 225, 190)

    def face_fn(dr, hcx, hcy, hr, col):
        # Big expressive cartoon eyes
        eye_r = max(4, hr // 4)
        pupil_r = max(3, hr // 6)
        sep = hr // 3
        for sx in [-sep, sep]:
            ex = hcx + sx
            ey = hcy - hr // 5
            dr.ellipse([ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r],
                       fill=(255, 255, 255), outline=col, width=2)
            dr.ellipse([ex - pupil_r + 1, ey - pupil_r + 1,
                        ex + pupil_r + 1, ey + pupil_r + 1], fill=(20, 20, 20))
            hl = max(1, pupil_r // 2)
            dr.ellipse([ex + 2, ey - 2, ex + hl + 2, ey + hl - 2],
                       fill=(255, 255, 255))
            # Thick eyebrow
            bw = eye_r + 3
            dr.line([(ex - bw, ey - eye_r - 6), (ex + bw, ey - eye_r - 8)],
                    fill=col, width=3)
        # Wide smile
        mw = int(hr * 0.55)
        dr.arc([hcx - mw, hcy + 2, hcx + mw, hcy + hr // 2],
               start=5, end=175, fill=col, width=3)

    def line_fn(p1, p2, c, w):
        # Draw thick stroked line  - body fill + outline
        draw.line([p1, p2], fill=c, width=w + 4)
        draw.line([p1, p2], fill=body_fill, width=max(1, w - 2))

    def joint_fn(pt):
        jr = 6
        draw.ellipse([pt[0] - jr, pt[1] - jr, pt[0] + jr, pt[1] + jr],
                     fill=body_fill, outline=outline, width=2)

    draw_common_figure(draw, cx, cy, d, 7, outline, head_fill,
                       face_fn, line_fn, joint_fn)


# ═══════════════════════════════════════════════════════════════
# STYLE 5: Pencil sketch  - textured gray lines, notebook paper bg
# ═══════════════════════════════════════════════════════════════
def render_style_pencil(cell):
    draw = ImageDraw.Draw(cell)
    # Notebook paper
    bg = (252, 250, 245)
    draw.rectangle([0, 0, CW, CH], fill=bg)
    # Lined paper
    for y in range(60, CH, 32):
        draw.line([(30, y), (CW - 30, y)], fill=(200, 210, 220), width=1)
    # Red margin
    draw.line([(65, 0), (65, CH)], fill=(220, 160, 160), width=1)

    np.random.seed(3)
    d = fig_dims(0.95)
    cx, cy = CW // 2 + 15, CH // 2 + 40
    pencil = (80, 75, 70)

    def face_fn(dr, hcx, hcy, hr, col):
        simple_face(dr, hcx, hcy, hr, pencil)

    def line_fn(p1, p2, c, w):
        # Double-stroke pencil effect
        wobble_line(draw, p1, p2, c, w)
        # Lighter second stroke slightly offset
        p1b = (p1[0] + 1, p1[1] + 1)
        p2b = (p2[0] + 1, p2[1] + 1)
        lighter = tuple(min(255, ch + 40) for ch in c)
        wobble_line(draw, p1b, p2b, lighter, max(1, w - 1))

    draw_common_figure(draw, cx, cy, d, 3, pencil, bg, face_fn, line_fn)


# ═══════════════════════════════════════════════════════════════
# STYLE 6: Neon glow  - glowing lines on dark background
# ═══════════════════════════════════════════════════════════════
def render_style_neon(cell):
    draw = ImageDraw.Draw(cell)
    draw.rectangle([0, 0, CW, CH], fill=(12, 12, 18))

    d = fig_dims(1.0)
    cx, cy = CW // 2, CH // 2 + 40
    neon_teal = (0, 255, 220)
    neon_amber = (255, 180, 50)

    # Draw glow layer (wider, semi-transparent)
    glow_layer = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    def face_fn(dr, hcx, hcy, hr, col):
        er = max(2, hr // 8)
        sep = hr // 3
        for sx in [-sep, sep]:
            dr.ellipse([hcx + sx - er, hcy - er - hr//6,
                        hcx + sx + er, hcy + er - hr//6], fill=neon_amber)
        mw = hr // 2
        dr.arc([hcx - mw, hcy, hcx + mw, hcy + hr // 3],
               start=15, end=165, fill=neon_teal, width=2)

    def line_fn(p1, p2, c, w):
        # Glow underneath
        glow_c = tuple(min(255, ch) for ch in c) + (60,)
        glow_draw.line([p1, p2], fill=glow_c, width=w + 8)
        draw.line([p1, p2], fill=c, width=w)

    draw_common_figure(draw, cx, cy, d, 3, neon_teal, (18, 18, 25),
                       face_fn, line_fn)

    # Composite glow
    blurred = glow_layer.filter(ImageFilter.GaussianBlur(6))
    cell_rgba = cell.convert("RGBA")
    cell_rgba = Image.alpha_composite(cell_rgba, blurred)
    cell.paste(cell_rgba.convert("RGB"))


# ═══════════════════════════════════════════════════════════════
# STYLE 7: Watercolor / soft pastel  - soft edges, color washes
# ═══════════════════════════════════════════════════════════════
def render_style_watercolor(cell):
    draw = ImageDraw.Draw(cell)
    # Soft watercolor paper
    for y in range(CH):
        t = y / CH
        r = int(250 - t * 8)
        g = int(245 - t * 6)
        b = int(240 - t * 5)
        draw.line([(0, y), (CW, y)], fill=(r, g, b))

    # Watercolor splotches behind figure
    splotch_layer = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(splotch_layer)
    np.random.seed(77)
    splotch_colors = [(180, 220, 215, 40), (220, 200, 160, 35),
                      (200, 180, 200, 30), (180, 210, 180, 35)]
    for _ in range(8):
        sx = np.random.randint(100, CW - 100)
        sy = np.random.randint(100, CH - 100)
        sr = np.random.randint(40, 120)
        sc = splotch_colors[np.random.randint(0, len(splotch_colors))]
        sdraw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=sc)
    splotch_blurred = splotch_layer.filter(ImageFilter.GaussianBlur(20))
    cell_rgba = cell.convert("RGBA")
    cell_rgba = Image.alpha_composite(cell_rgba, splotch_blurred)
    cell.paste(cell_rgba.convert("RGB"))
    draw = ImageDraw.Draw(cell)

    d = fig_dims(1.0)
    cx, cy = CW // 2, CH // 2 + 40
    ink = (90, 75, 65)
    skin = (245, 225, 210)

    def face_fn(dr, hcx, hcy, hr, col):
        er = max(2, hr // 7)
        sep = hr // 3
        for sx in [-sep, sep]:
            dr.ellipse([hcx + sx - er, hcy - er - hr//6,
                        hcx + sx + er, hcy + er - hr//6], fill=(70, 60, 55))
        mw = hr // 2
        dr.arc([hcx - mw, hcy + 2, hcx + mw, hcy + hr // 3],
               start=10, end=170, fill=(70, 60, 55), width=2)

    def line_fn(p1, p2, c, w):
        # Soft brushstroke: wider translucent + narrow core  
        wobble_line(draw, p1, p2, c, w)

    draw_common_figure(draw, cx, cy, d, 4, ink, skin, face_fn, line_fn)

    # Soft blur pass on whole thing for watercolor softness
    blurred = cell.filter(ImageFilter.GaussianBlur(0.8))
    cell.paste(blurred)


# ═══════════════════════════════════════════════════════════════
# STYLE 8: Geometric / modern flat  - clean shapes, flat colors, no outlines
# ═══════════════════════════════════════════════════════════════
def render_style_geometric(cell):
    draw = ImageDraw.Draw(cell)
    # Flat teal background
    bg = (26, 107, 106)
    draw.rectangle([0, 0, CW, CH], fill=bg)

    d = fig_dims(1.1)
    cx, cy = CW // 2, CH // 2 + 40
    body_color = (250, 247, 242)  # warm white
    accent = (212, 146, 42)  # amber

    # Head  - clean circle
    head_cy = cy - d["torso"] - d["head_r"] - 8
    draw.ellipse([cx - d["head_r"], head_cy - d["head_r"],
                  cx + d["head_r"], head_cy + d["head_r"]],
                 fill=body_color)

    # Simple face
    er = max(2, d["head_r"] // 7)
    sep = d["head_r"] // 3
    for sx in [-sep, sep]:
        draw.ellipse([cx + sx - er, head_cy - er - d["head_r"]//6,
                      cx + sx + er, head_cy + er - d["head_r"]//6], fill=bg)
    mw = d["head_r"] // 2
    draw.arc([cx - mw, head_cy + 2, cx + mw, head_cy + d["head_r"] // 3 + 2],
             start=10, end=170, fill=bg, width=2)

    def face_fn(dr, hcx, hcy, hr, col):
        pass  # already drawn above

    def line_fn(p1, p2, c, w):
        # Rounded ends via circles at joints
        draw.line([p1, p2], fill=c, width=w)

    def joint_fn(pt):
        jr = 5
        draw.ellipse([pt[0] - jr, pt[1] - jr, pt[0] + jr, pt[1] + jr],
                     fill=body_color)

    draw_common_figure(draw, cx, cy, d, 6, body_color, body_color,
                       face_fn, line_fn, joint_fn)

    # Accent shapes
    draw.rectangle([cx - 60, cy + d["upper_leg"] + d["lower_leg"] + 10,
                    cx + 60, cy + d["upper_leg"] + d["lower_leg"] + 14],
                   fill=accent)


# ═══════════════════════════════════════════════════════════════


STYLES = [
    ("A. Current Style",
     "Warm white figure on kitchen photo,\nskin-toned fill, hand-drawn wobble lines",
     render_style_current),
    ("B. Classic Minimal",
     "Thin black on white, XKCD-style.\nClean, simple, internet-native",
     render_style_minimal),
    ("C. Chalkboard",
     "White chalk on dark green board.\nSketchy lines, chalk dust texture",
     render_style_whiteboard),
    ("D. Bold Cartoon",
     "Thick outlines, skin-tone fill, joints.\nTheOdd1sOut / Diary of a Wimpy Kid",
     render_style_bold_cartoon),
    ("E. Pencil Sketch",
     "Gray pencil on notebook paper.\nLined paper bg, double-stroke texture",
     render_style_pencil),
    ("F. Neon Glow",
     "Glowing teal lines on black.\nCyberpunk/electric feel",
     render_style_neon),
    ("G. Watercolor",
     "Soft brushstroke lines on warm paper.\nPastel splotches, gentle edges",
     render_style_watercolor),
    ("H. Geometric Flat",
     "Clean shapes, your brand teal bg.\nModern/minimal, no outlines on limbs",
     render_style_geometric),
]


def build_sampler():
    sheet = Image.new("RGB", (SHEET_W, SHEET_H), (255, 255, 255))
    sheet_draw = ImageDraw.Draw(sheet)

    # Title
    title_font = load_font(FONTS_DIR / "Montserrat-Black.ttf", 36)
    sheet_draw.text((SHEET_W // 2 - 280, 20),
                    "STICK FIGURE STYLE OPTIONS", fill=(30, 30, 30),
                    font=title_font)

    for idx, (name, desc, render_fn) in enumerate(STYLES):
        col = idx % COLS
        row = idx // COLS
        x0 = col * CW
        y0 = row * CH + 80

        # Create cell
        cell = Image.new("RGB", (CW, CH), (200, 200, 200))
        render_fn(cell)

        # Label bar at bottom
        cell_draw = ImageDraw.Draw(cell)
        bar_y = CH - 80
        cell_draw.rectangle([0, bar_y, CW, CH], fill=(255, 255, 255))
        cell_draw.line([(0, bar_y), (CW, bar_y)], fill=(200, 195, 190), width=2)
        cell_draw.text((12, bar_y + 6), name, fill=(30, 30, 30), font=FONT_LABEL)
        cell_draw.text((12, bar_y + 32), desc, fill=(100, 95, 90), font=FONT_DESC)

        # Border
        cell_draw.rectangle([0, 0, CW - 1, CH - 1], outline=(180, 175, 170), width=2)

        sheet.paste(cell, (x0, y0))

    out = "/tmp/stick-figure-styles.png"
    sheet.save(out, quality=95)
    print(f"Saved style sampler: {out}")
    print(f"  {SHEET_W}x{SHEET_H} px, {COLS}x{ROWS} grid")
    return out


if __name__ == "__main__":
    build_sampler()
