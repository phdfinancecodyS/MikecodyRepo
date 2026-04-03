#!/usr/bin/env python3
"""
Style Sampler v2 — "Fuller body + stick limbs" variations.
All options have a rounded/filled torso with stick arms, legs, and round head.

Output: /tmp/stick-figure-styles-v2.png
"""
import math
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "assets" / "fonts"

def load_font(path, size):
    try:
        return ImageFont.truetype(str(path), size)
    except (OSError, IOError):
        return ImageFont.load_default()

FONT_LABEL = load_font(FONTS_DIR / "Montserrat-Bold.ttf", 22)
FONT_DESC = load_font(FONTS_DIR / "Montserrat-Regular.ttf", 15)

CW, CH = 540, 750
COLS, ROWS = 4, 2
SHEET_W = CW * COLS
SHEET_H = CH * ROWS + 80

# Kitchen bg simulation for all panels
def draw_kitchen_bg(draw, w, h):
    for y in range(h):
        t = y / h
        c = int(32 + t * 22)
        draw.line([(0, y), (w, y)], fill=(c, c - 2, c - 5))
    # Counter
    counter_y = int(h * 0.68)
    draw.rectangle([0, counter_y, w, counter_y + 8], fill=(90, 80, 70))
    draw.rectangle([0, counter_y + 8, w, h], fill=(60, 55, 48))
    return counter_y

def ik_arm(shoulder, hand, upper_len, fore_len, bend_dir=1):
    dx = hand[0] - shoulder[0]
    dy = hand[1] - shoulder[1]
    dist = min(math.sqrt(dx*dx + dy*dy), upper_len + fore_len - 1)
    angle_to_hand = math.atan2(dy, dx)
    cos_e = (upper_len**2 + dist**2 - fore_len**2) / (2 * upper_len * dist + 1e-6)
    cos_e = max(-1, min(1, cos_e))
    elbow_angle = angle_to_hand + math.acos(cos_e) * bend_dir
    ex = shoulder[0] + int(upper_len * math.cos(elbow_angle))
    ey = shoulder[1] + int(upper_len * math.sin(elbow_angle))
    return (ex, ey)

def wobble_line(draw, p1, p2, color, width, segments=6):
    pts = [p1]
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    seg_len = math.sqrt(dx*dx + dy*dy)
    if seg_len < 1: return
    nx, ny = -dy / seg_len, dx / seg_len
    for i in range(1, segments):
        t = i / segments
        mx = p1[0] + dx * t + nx * np.random.normal(0, seg_len * 0.018)
        my = p1[1] + dy * t + ny * np.random.normal(0, seg_len * 0.018)
        pts.append((int(mx), int(my)))
    pts.append(p2)
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=color, width=width)

def simple_eyes(draw, cx, cy, r, color=(45, 40, 35)):
    """Dot eyes + gentle smile"""
    er = max(2, r // 7)
    sep = int(r * 0.35)
    for sx in [-sep, sep]:
        draw.ellipse([cx + sx - er, cy - er - r//6,
                      cx + sx + er, cy + er - r//6], fill=color)
    mw = int(r * 0.4)
    draw.arc([cx - mw, cy + r * 0.05, cx + mw, cy + r * 0.35],
             start=10, end=170, fill=color, width=2)

def expressive_eyes(draw, cx, cy, r, color=(45, 40, 35)):
    """White eyes with pupils, brows, smile"""
    eye_r = max(3, int(r * 0.22))
    pupil_r = max(2, int(r * 0.13))
    sep = int(r * 0.35)
    for sx in [-sep, sep]:
        ex, ey = cx + sx, cy - int(r * 0.12)
        draw.ellipse([ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r],
                     fill=(255, 255, 255))
        draw.ellipse([ex - pupil_r + 1, ey - pupil_r,
                      ex + pupil_r + 1, ey + pupil_r], fill=color)
        hl = max(1, pupil_r // 2)
        draw.ellipse([ex + 1, ey - pupil_r + 1, ex + hl + 1, ey],
                     fill=(255, 255, 255))
        # Eyebrow
        bw = eye_r + 2
        draw.line([(ex - bw, ey - eye_r - 5), (ex + bw, ey - eye_r - 7)],
                  fill=color, width=2)
    mw = int(r * 0.42)
    draw.arc([cx - mw, cy + 2, cx + mw, cy + int(r * 0.4)],
             start=8, end=172, fill=color, width=2)


# ── Common arm/leg drawing for all styles ──
def draw_stick_limbs(draw, cx, body_top, body_bottom, body_half_w,
                     counter_y, lw, color, line_fn=None, with_hands=True):
    """Draw stick arms + legs attached to a filled body.
    Returns nothing — draws directly."""
    if line_fn is None:
        line_fn = lambda p1, p2, c, w: draw.line([p1, p2], fill=c, width=w)

    arm_len_u = 50
    arm_len_f = 44
    # Shoulder attach points (sides of body)
    l_sh = (cx - body_half_w + 2, body_top + 12)
    r_sh = (cx + body_half_w - 2, body_top + 12)

    # Right hand up (chopping)
    r_hand = (cx + body_half_w + 38, body_top - 20)
    r_elbow = ik_arm(r_sh, r_hand, arm_len_u, arm_len_f, bend_dir=-1)
    line_fn(r_sh, r_elbow, color, lw)
    line_fn(r_elbow, r_hand, color, lw)

    # Left hand resting
    l_hand = (cx - body_half_w - 28, body_bottom - 15)
    l_elbow = ik_arm(l_sh, l_hand, arm_len_u, arm_len_f, bend_dir=1)
    line_fn(l_sh, l_elbow, color, lw)
    line_fn(l_elbow, l_hand, color, lw)

    # Hand circles
    if with_hands:
        hr = 5
        for h in [r_hand, l_hand]:
            draw.ellipse([h[0]-hr, h[1]-hr, h[0]+hr, h[1]+hr],
                         fill=(250, 240, 230), outline=color, width=2)

    # Knife in right hand
    k_len = 26
    k_angle = math.pi / 2 + 0.3
    kx = r_hand[0] + int(k_len * math.cos(k_angle))
    ky = r_hand[1] + int(k_len * math.sin(k_angle))
    line_fn(r_hand, (kx, ky), (180, 185, 190), max(2, lw - 1))

    # Legs (going behind counter)
    leg_len = 55
    l_foot = (cx - 18, body_bottom + leg_len)
    r_foot = (cx + 18, body_bottom + leg_len)
    line_fn((cx - 8, body_bottom), l_foot, color, lw)
    line_fn((cx + 8, body_bottom), r_foot, color, lw)
    # Feet
    if with_hands:
        for f in [l_foot, r_foot]:
            draw.ellipse([f[0]-4, f[1]-3, f[0]+6, f[1]+4],
                         fill=color)


# ═══════════════════════════════════════════════════════════════
# STYLE A: Pill body (Cyanide & Happiness style)
# Rounded rectangle torso, stick limbs, round head on top
# ═══════════════════════════════════════════════════════════════
def render_pill_body(cell):
    draw = ImageDraw.Draw(cell)
    counter_y = draw_kitchen_bg(draw, CW, CH)
    np.random.seed(10)

    cx = CW // 2
    body_w, body_h = 52, 90
    body_top = counter_y - body_h - 60
    body_bottom = body_top + body_h
    head_r = 28
    head_cy = body_top - head_r - 4
    color = (240, 235, 225)
    outline = (45, 40, 35)
    skin = (250, 245, 235)
    lw = 3

    # Body — pill / rounded rect
    draw.rounded_rectangle([cx - body_w//2, body_top, cx + body_w//2, body_bottom],
                           radius=22, fill=color, outline=outline, width=3)

    # Neck
    draw.line([(cx, body_top), (cx, head_cy + head_r)], fill=outline, width=lw)

    # Head
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
                 fill=skin, outline=outline, width=3)
    expressive_eyes(draw, cx, head_cy, head_r, outline)

    # Hair tufts
    for dx, dy, l in [(-12, -5, 18), (0, -10, 22), (10, -3, 16)]:
        draw.line([(cx + dx, head_cy - head_r + dy),
                   (cx + dx + 3, head_cy - head_r + dy - l)],
                  fill=(80, 70, 60), width=3)

    draw_stick_limbs(draw, cx, body_top, body_bottom, body_w//2,
                     counter_y, lw, outline)


# ═══════════════════════════════════════════════════════════════
# STYLE B: Bean / pear body — wider hips, narrower shoulders
# ═══════════════════════════════════════════════════════════════
def render_bean_body(cell):
    draw = ImageDraw.Draw(cell)
    counter_y = draw_kitchen_bg(draw, CW, CH)
    np.random.seed(11)

    cx = CW // 2
    head_r = 28
    body_top_w = 38
    body_bot_w = 52
    body_h = 95
    body_top = counter_y - body_h - 55
    body_bottom = body_top + body_h
    head_cy = body_top - head_r - 4
    color = (240, 235, 225)
    outline = (45, 40, 35)
    skin = (250, 245, 235)
    lw = 3

    # Bean body — trapezoid with rounded corners
    body_pts = [
        (cx - body_top_w, body_top + 10),
        (cx + body_top_w, body_top + 10),
        (cx + body_bot_w, body_bottom - 8),
        (cx + body_bot_w - 8, body_bottom),
        (cx - body_bot_w + 8, body_bottom),
        (cx - body_bot_w, body_bottom - 8),
    ]
    draw.polygon(body_pts, fill=color, outline=outline)
    # Smooth the top with an arc
    draw.arc([cx - body_top_w, body_top - 2, cx + body_top_w, body_top + 22],
             start=180, end=360, fill=outline, width=3)
    draw.rectangle([cx - body_top_w + 1, body_top + 10,
                    cx + body_top_w - 1, body_top + 14], fill=color)

    draw.line([(cx, body_top), (cx, head_cy + head_r)], fill=outline, width=lw)
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
                 fill=skin, outline=outline, width=3)
    expressive_eyes(draw, cx, head_cy, head_r, outline)
    for dx, dy, l in [(-12, -5, 18), (0, -10, 22), (10, -3, 16)]:
        draw.line([(cx + dx, head_cy - head_r + dy),
                   (cx + dx + 3, head_cy - head_r + dy - l)],
                  fill=(80, 70, 60), width=3)

    draw_stick_limbs(draw, cx, body_top + 10, body_bottom, body_top_w,
                     counter_y, lw, outline)


# ═══════════════════════════════════════════════════════════════
# STYLE C: Oval / egg body — simple and clean
# ═══════════════════════════════════════════════════════════════
def render_oval_body(cell):
    draw = ImageDraw.Draw(cell)
    counter_y = draw_kitchen_bg(draw, CW, CH)
    np.random.seed(12)

    cx = CW // 2
    head_r = 26
    body_rx, body_ry = 34, 52
    body_cy = counter_y - body_ry - 55
    body_top = body_cy - body_ry
    body_bottom = body_cy + body_ry
    head_cy = body_top - head_r - 6
    color = (240, 235, 225)
    outline = (45, 40, 35)
    skin = (250, 245, 235)
    lw = 3

    # Oval body
    draw.ellipse([cx - body_rx, body_cy - body_ry,
                  cx + body_rx, body_cy + body_ry],
                 fill=color, outline=outline, width=3)

    draw.line([(cx, body_top), (cx, head_cy + head_r)], fill=outline, width=lw)
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
                 fill=skin, outline=outline, width=3)
    expressive_eyes(draw, cx, head_cy, head_r, outline)
    for dx, dy, l in [(-12, -5, 18), (0, -10, 22), (10, -3, 16)]:
        draw.line([(cx + dx, head_cy - head_r + dy),
                   (cx + dx + 3, head_cy - head_r + dy - l)],
                  fill=(80, 70, 60), width=3)

    draw_stick_limbs(draw, cx, body_top + 8, body_bottom, body_rx,
                     counter_y, lw, outline)


# ═══════════════════════════════════════════════════════════════
# STYLE D: T-shirt body — rectangular with shirt/clothing hint
# ═══════════════════════════════════════════════════════════════
def render_tshirt_body(cell):
    draw = ImageDraw.Draw(cell)
    counter_y = draw_kitchen_bg(draw, CW, CH)
    np.random.seed(13)

    cx = CW // 2
    head_r = 27
    body_w, body_h = 56, 85
    body_top = counter_y - body_h - 58
    body_bottom = body_top + body_h
    head_cy = body_top - head_r - 4
    outline = (45, 40, 35)
    skin = (250, 245, 235)
    shirt_color = (26, 107, 106)  # brand teal!
    lw = 3

    # T-shirt body — rectangle with sleeves
    # Main body
    draw.rounded_rectangle([cx - body_w//2, body_top, cx + body_w//2, body_bottom],
                           radius=8, fill=shirt_color, outline=outline, width=2)
    # Sleeve bumps
    sleeve_w = 16
    sleeve_h = 22
    for sx in [-1, 1]:
        sx0 = cx + sx * body_w // 2
        sx1 = sx0 + sx * sleeve_w
        draw.rounded_rectangle([min(sx0, sx1), body_top + 3,
                                max(sx0, sx1), body_top + 3 + sleeve_h],
                               radius=6, fill=shirt_color, outline=outline, width=2)

    # Neckline
    draw.arc([cx - 14, body_top - 6, cx + 14, body_top + 12],
             start=0, end=180, fill=outline, width=2)

    draw.line([(cx, body_top - 2), (cx, head_cy + head_r)], fill=outline, width=lw)
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
                 fill=skin, outline=outline, width=3)
    expressive_eyes(draw, cx, head_cy, head_r, outline)
    for dx, dy, l in [(-12, -5, 18), (0, -10, 22), (10, -3, 16)]:
        draw.line([(cx + dx, head_cy - head_r + dy),
                   (cx + dx + 3, head_cy - head_r + dy - l)],
                  fill=(80, 70, 60), width=3)

    draw_stick_limbs(draw, cx, body_top, body_bottom, body_w//2 + sleeve_w,
                     counter_y, lw, outline)


# ═══════════════════════════════════════════════════════════════
# STYLE E: Rounded rectangle + big head (chibi proportions)
# ═══════════════════════════════════════════════════════════════
def render_chibi_body(cell):
    draw = ImageDraw.Draw(cell)
    counter_y = draw_kitchen_bg(draw, CW, CH)
    np.random.seed(14)

    cx = CW // 2
    head_r = 38  # bigger head!
    body_w, body_h = 46, 70
    body_top = counter_y - body_h - 55
    body_bottom = body_top + body_h
    head_cy = body_top - head_r - 2
    color = (240, 235, 225)
    outline = (45, 40, 35)
    skin = (250, 245, 235)
    lw = 3

    # Smaller rounded body
    draw.rounded_rectangle([cx - body_w//2, body_top, cx + body_w//2, body_bottom],
                           radius=18, fill=color, outline=outline, width=3)

    # No visible neck — head sits right on body
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
                 fill=skin, outline=outline, width=3)
    expressive_eyes(draw, cx, head_cy, head_r, outline)
    for dx, dy, l in [(-15, -3, 20), (-3, -10, 26), (12, -5, 18), (22, 2, 12)]:
        draw.line([(cx + dx, head_cy - head_r + dy),
                   (cx + dx + 3, head_cy - head_r + dy - l)],
                  fill=(80, 70, 60), width=3)

    draw_stick_limbs(draw, cx, body_top, body_bottom, body_w//2,
                     counter_y, lw, outline)


# ═══════════════════════════════════════════════════════════════
# STYLE F: Wobble/hand-drawn pill body — same as A but sketchy lines
# ═══════════════════════════════════════════════════════════════
def render_sketchy_pill(cell):
    draw = ImageDraw.Draw(cell)
    counter_y = draw_kitchen_bg(draw, CW, CH)
    np.random.seed(15)

    cx = CW // 2
    body_w, body_h = 52, 88
    body_top = counter_y - body_h - 60
    body_bottom = body_top + body_h
    head_r = 28
    head_cy = body_top - head_r - 4
    color = (240, 235, 225)
    outline = (45, 40, 35)
    skin = (250, 245, 235)
    lw = 3

    # Multiple slightly-offset outlines for hand-drawn feel
    for offset in range(3):
        ox = np.random.randint(-1, 2)
        oy = np.random.randint(-1, 2)
        a = max(80, 180 - offset * 50)
        col = (45, 40, 35)
        draw.rounded_rectangle([cx - body_w//2 + ox, body_top + oy,
                                cx + body_w//2 + ox, body_bottom + oy],
                               radius=22, outline=col, width=2)
    draw.rounded_rectangle([cx - body_w//2, body_top, cx + body_w//2, body_bottom],
                           radius=22, fill=color, outline=outline, width=3)

    wobble_line(draw, (cx, body_top), (cx, head_cy + head_r), outline, lw)

    # Sketchy head — double outline
    for offset in range(2):
        ox = np.random.randint(-1, 2)
        oy = np.random.randint(-1, 2)
        draw.ellipse([cx - head_r + ox, head_cy - head_r + oy,
                      cx + head_r + ox, head_cy + head_r + oy],
                     outline=(60, 55, 48), width=2)
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
                 fill=skin, outline=outline, width=3)
    expressive_eyes(draw, cx, head_cy, head_r, outline)
    for dx, dy, l in [(-12, -5, 18), (0, -10, 22), (10, -3, 16)]:
        wobble_line(draw, (cx + dx, head_cy - head_r + dy),
                    (cx + dx + 3, head_cy - head_r + dy - l),
                    (80, 70, 60), 3, segments=3)

    def wline(p1, p2, c, w):
        wobble_line(draw, p1, p2, c, w)

    draw_stick_limbs(draw, cx, body_top, body_bottom, body_w//2,
                     counter_y, lw, outline, line_fn=wline)


# ═══════════════════════════════════════════════════════════════
# STYLE G: Apron body — pill with an apron for the cooking context
# ═══════════════════════════════════════════════════════════════
def render_apron_body(cell):
    draw = ImageDraw.Draw(cell)
    counter_y = draw_kitchen_bg(draw, CW, CH)
    np.random.seed(16)

    cx = CW // 2
    body_w, body_h = 52, 92
    body_top = counter_y - body_h - 58
    body_bottom = body_top + body_h
    head_r = 28
    head_cy = body_top - head_r - 4
    outline = (45, 40, 35)
    skin = (250, 245, 235)
    lw = 3

    # Body base
    draw.rounded_rectangle([cx - body_w//2, body_top, cx + body_w//2, body_bottom],
                           radius=20, fill=(240, 235, 225), outline=outline, width=3)

    # Apron overlay
    apron_color = (250, 247, 242)  # warm white
    apron_top = body_top + 15
    apron_w = body_w // 2 - 4
    draw.rounded_rectangle([cx - apron_w, apron_top, cx + apron_w, body_bottom - 5],
                           radius=8, fill=apron_color, outline=outline, width=2)
    # Apron neck strap
    draw.line([(cx - apron_w + 4, apron_top), (cx - 6, body_top + 3)],
              fill=outline, width=2)
    draw.line([(cx + apron_w - 4, apron_top), (cx + 6, body_top + 3)],
              fill=outline, width=2)
    # Apron pocket
    pocket_w = 14
    pocket_h = 12
    draw.rounded_rectangle([cx - pocket_w, body_bottom - 35,
                            cx + pocket_w, body_bottom - 35 + pocket_h],
                           radius=3, outline=outline, width=1)

    draw.line([(cx, body_top), (cx, head_cy + head_r)], fill=outline, width=lw)
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
                 fill=skin, outline=outline, width=3)
    expressive_eyes(draw, cx, head_cy, head_r, outline)
    for dx, dy, l in [(-12, -5, 18), (0, -10, 22), (10, -3, 16)]:
        draw.line([(cx + dx, head_cy - head_r + dy),
                   (cx + dx + 3, head_cy - head_r + dy - l)],
                  fill=(80, 70, 60), width=3)

    draw_stick_limbs(draw, cx, body_top, body_bottom, body_w//2,
                     counter_y, lw, outline)


# ═══════════════════════════════════════════════════════════════
# STYLE H: Soft/rounded — thicker limbs, rounder everything, gentle
# ═══════════════════════════════════════════════════════════════
def render_soft_rounded(cell):
    draw = ImageDraw.Draw(cell)
    counter_y = draw_kitchen_bg(draw, CW, CH)
    np.random.seed(17)

    cx = CW // 2
    head_r = 30
    body_rx, body_ry = 36, 50
    body_cy = counter_y - body_ry - 56
    body_top = body_cy - body_ry
    body_bottom = body_cy + body_ry
    head_cy_pos = body_top - head_r - 2
    outline = (65, 58, 52)  # softer outline
    skin = (252, 248, 240)
    body_fill = (245, 240, 232)
    lw = 4  # thicker, rounder limbs

    # Soft oval body
    # Shadow
    draw.ellipse([cx - body_rx + 3, body_cy - body_ry + 3,
                  cx + body_rx + 3, body_cy + body_ry + 3],
                 fill=(25, 22, 18))
    draw.ellipse([cx - body_rx, body_cy - body_ry,
                  cx + body_rx, body_cy + body_ry],
                 fill=body_fill, outline=outline, width=3)

    # No neck — head overlaps body slightly
    draw.ellipse([cx - head_r, head_cy_pos - head_r,
                  cx + head_r, head_cy_pos + head_r],
                 fill=skin, outline=outline, width=3)
    expressive_eyes(draw, cx, head_cy_pos, head_r, (55, 50, 45))
    # Soft hair
    for dx, dy, l in [(-14, -2, 16), (-4, -8, 20), (8, -6, 17), (18, 0, 12)]:
        draw.line([(cx + dx, head_cy_pos - head_r + dy),
                   (cx + dx + 2, head_cy_pos - head_r + dy - l)],
                  fill=(90, 80, 70), width=3)

    # Slightly thicker limbs
    def thick_line(p1, p2, c, w):
        draw.line([p1, p2], fill=c, width=w + 2)
        # Round caps
        for pt in [p1, p2]:
            r = (w + 2) // 2
            draw.ellipse([pt[0]-r, pt[1]-r, pt[0]+r, pt[1]+r], fill=c)

    draw_stick_limbs(draw, cx, body_top + 8, body_bottom, body_rx,
                     counter_y, lw, outline, line_fn=thick_line)


STYLES = [
    ("A. Pill Body",
     "Rounded rectangle torso, stick limbs.\nCyanide & Happiness / Henry Stickmin",
     render_pill_body),
    ("B. Bean / Pear",
     "Wider at hips, narrower shoulders.\nOrganic, approachable shape",
     render_bean_body),
    ("C. Oval / Egg",
     "Simple ellipse torso.\nClean, friendly, minimal",
     render_oval_body),
    ("D. T-Shirt",
     "Rectangular body with shirt + sleeves.\nClothed feel, brand teal shirt",
     render_tshirt_body),
    ("E. Chibi / Big Head",
     "Oversized head, small rounded body.\nCute, expressive, cartoony",
     render_chibi_body),
    ("F. Sketchy Pill",
     "Same pill shape but hand-drawn wobble.\nOrganic + imperfect feel",
     render_sketchy_pill),
    ("G. Apron Chef",
     "Pill body with cooking apron + pocket.\nOn-theme for kitchen setting",
     render_apron_body),
    ("H. Soft & Rounded",
     "Thicker limbs, round joints, gentle.\nWarm, therapeutic, approachable",
     render_soft_rounded),
]


def build_sampler():
    sheet = Image.new("RGB", (SHEET_W, SHEET_H), (255, 255, 255))
    sheet_draw = ImageDraw.Draw(sheet)

    title_font = load_font(FONTS_DIR / "Montserrat-Black.ttf", 34)
    sheet_draw.text((SHEET_W // 2 - 380, 20),
                    'FULLER BODY + STICK LIMBS — STYLE OPTIONS',
                    fill=(30,30,30), font=title_font)

    for idx, (name, desc, render_fn) in enumerate(STYLES):
        col = idx % COLS
        row = idx // COLS
        x0 = col * CW
        y0 = row * CH + 80

        cell = Image.new("RGB", (CW, CH), (200, 200, 200))
        render_fn(cell)

        cell_draw = ImageDraw.Draw(cell)
        bar_y = CH - 85
        cell_draw.rectangle([0, bar_y, CW, CH], fill=(255, 255, 255))
        cell_draw.line([(0, bar_y), (CW, bar_y)], fill=(200, 195, 190), width=2)
        cell_draw.text((12, bar_y + 6), name, fill=(30, 30, 30), font=FONT_LABEL)
        cell_draw.text((12, bar_y + 34), desc, fill=(100, 95, 90), font=FONT_DESC)
        cell_draw.rectangle([0, 0, CW-1, CH-1], outline=(180, 175, 170), width=2)

        sheet.paste(cell, (x0, y0))

    out = "/tmp/stick-figure-styles-v2.png"
    sheet.save(out, quality=95)
    print(f"Saved: {out}  ({SHEET_W}x{SHEET_H})")
    return out


if __name__ == "__main__":
    build_sampler()
