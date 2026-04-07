"""
Generate Ask Anyway free guide PDFs.
Outputs to ask-anyway-deploy/guides/
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import PageBreak

OUT_DIR = os.path.join(os.path.dirname(__file__), "ask-anyway-deploy", "guides")
os.makedirs(OUT_DIR, exist_ok=True)

# ─── Colours ─────────────────────────────────────────────────
BG        = HexColor("#000000")
CREAM     = HexColor("#f0ece4")
MUTED     = HexColor("#888888")
DIM       = HexColor("#555555")
BORDER    = HexColor("#282828")
SURFACE   = HexColor("#0d0d0d")
GREEN     = HexColor("#22c55e")
RED       = HexColor("#c06060")
AMBER     = HexColor("#f59e0b")
BLUE_DIM  = HexColor("#4060c0")
SCRIPT_BG = HexColor("#0a0a0a")
CRISIS_BG = HexColor("#0a0000")

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch

# ─── Helper: build doc with black background ─────────────────
def make_doc(path, title):
    doc = SimpleDocTemplate(
        path,
        pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.6*inch, bottomMargin=0.7*inch,
        title=title,
        author="Ask Anyway",
    )
    return doc

# ─── Page canvas (black bg + footer) ─────────────────────────
def make_canvas_fn(footer_text):
    def on_page(canvas, doc):
        canvas.saveState()
        # Black background
        canvas.setFillColor(BG)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        # Footer
        canvas.setFillColor(DIM)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(PAGE_W / 2, 0.35 * inch, footer_text)
        canvas.restoreState()
    return on_page

# ─── Shared styles ────────────────────────────────────────────
def make_styles():
    s = {}

    s["eyebrow"] = ParagraphStyle("eyebrow",
        fontName="Helvetica-Bold", fontSize=7,
        textColor=MUTED, spaceAfter=8, leading=9,
        letterSpacing=2,
    )
    s["h1"] = ParagraphStyle("h1",
        fontName="Helvetica-Bold", fontSize=28,
        textColor=CREAM, spaceAfter=12, leading=32,
    )
    s["h2"] = ParagraphStyle("h2",
        fontName="Helvetica-Bold", fontSize=16,
        textColor=CREAM, spaceAfter=8, leading=20,
    )
    s["h3"] = ParagraphStyle("h3",
        fontName="Helvetica-Bold", fontSize=11,
        textColor=CREAM, spaceAfter=6, leading=14,
    )
    s["body"] = ParagraphStyle("body",
        fontName="Helvetica", fontSize=10,
        textColor=HexColor("#b0aca5"), spaceAfter=10, leading=16,
    )
    s["body_strong"] = ParagraphStyle("body_strong",
        fontName="Helvetica-Bold", fontSize=10,
        textColor=CREAM, spaceAfter=10, leading=16,
    )
    s["small"] = ParagraphStyle("small",
        fontName="Helvetica", fontSize=8,
        textColor=MUTED, spaceAfter=6, leading=12,
    )
    s["section_label"] = ParagraphStyle("section_label",
        fontName="Helvetica-Bold", fontSize=7,
        textColor=DIM, spaceAfter=6, leading=9,
        letterSpacing=2,
    )
    s["script"] = ParagraphStyle("script",
        fontName="Helvetica-Oblique", fontSize=10,
        textColor=HexColor("#d4d0c8"), spaceAfter=6, leading=16,
        leftIndent=14, rightIndent=14,
    )
    s["script_em"] = ParagraphStyle("script_em",
        fontName="Helvetica", fontSize=8.5,
        textColor=DIM, spaceAfter=4, leading=12,
        leftIndent=14,
    )
    s["callout"] = ParagraphStyle("callout",
        fontName="Helvetica", fontSize=9.5,
        textColor=HexColor("#8eb898"), spaceAfter=6, leading=15,
        leftIndent=12, rightIndent=12,
    )
    s["crisis"] = ParagraphStyle("crisis",
        fontName="Helvetica", fontSize=10,
        textColor=HexColor("#a08080"), spaceAfter=6, leading=15,
        leftIndent=10,
    )
    s["crisis_num"] = ParagraphStyle("crisis_num",
        fontName="Helvetica-Bold", fontSize=10,
        textColor=RED, spaceAfter=4, leading=14,
    )
    s["step_title"] = ParagraphStyle("step_title",
        fontName="Helvetica-Bold", fontSize=10,
        textColor=CREAM, spaceAfter=3, leading=14,
    )
    s["step_desc"] = ParagraphStyle("step_desc",
        fontName="Helvetica", fontSize=9.5,
        textColor=MUTED, spaceAfter=0, leading=14,
    )
    s["res_title"] = ParagraphStyle("res_title",
        fontName="Helvetica-Bold", fontSize=9.5,
        textColor=HexColor("#cccccc"), spaceAfter=2, leading=13,
    )
    s["res_url"] = ParagraphStyle("res_url",
        fontName="Helvetica", fontSize=8.5,
        textColor=DIM, spaceAfter=0, leading=12,
    )
    s["check_label"] = ParagraphStyle("check_label",
        fontName="Helvetica", fontSize=10.5,
        textColor=HexColor("#b0aca5"), spaceAfter=0, leading=15,
    )
    s["check_section"] = ParagraphStyle("check_section",
        fontName="Helvetica-Bold", fontSize=8,
        textColor=DIM, spaceAfter=0, leading=10,
        letterSpacing=1.5,
    )
    s["reflection"] = ParagraphStyle("reflection",
        fontName="Helvetica", fontSize=9.5,
        textColor=HexColor("#8eb898"), spaceAfter=8, leading=15,
        leftIndent=10, rightIndent=10,
    )
    s["disclaimer"] = ParagraphStyle("disclaimer",
        fontName="Helvetica", fontSize=7.5,
        textColor=HexColor("#444444"), spaceAfter=0, leading=11,
    )
    s["free_badge"] = ParagraphStyle("free_badge",
        fontName="Helvetica-Bold", fontSize=7,
        textColor=GREEN, spaceAfter=16, leading=9,
        letterSpacing=1,
    )
    return s

# ─── Divider ─────────────────────────────────────────────────
def divider():
    return HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=20, spaceBefore=8)

def section_divider():
    return HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=16, spaceBefore=24)

# ─── Script box ──────────────────────────────────────────────
def script_box(lines, styles):
    rows = []
    for line in lines:
        if line.startswith("__em__"):
            rows.append(Paragraph(line[6:], styles["script_em"]))
        else:
            rows.append(Paragraph(line, styles["script"]))
    t = Table([[rows]], colWidths=[PAGE_W - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), SCRIPT_BG),
        ("BOX",        (0,0), (-1,-1), 0.5, BORDER),
        ("LEFTPADDING",  (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING",   (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0), (-1,-1), 12),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), 6),
    ]))
    return t

# ─── Callout box ─────────────────────────────────────────────
def callout_box(text, styles, bg=HexColor("#0a0e0a"), border=HexColor("#1a2e1a"), color=None):
    if color:
        styles["callout"].textColor = color
    p = Paragraph(text, styles["callout"])
    t = Table([[p]], colWidths=[PAGE_W - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("BOX",        (0,0), (-1,-1), 0.5, border),
        ("LEFTPADDING",  (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING",   (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0), (-1,-1), 12),
    ]))
    return t

# ─── Step row ────────────────────────────────────────────────
def step_row(num, title, desc, styles):
    left = Paragraph(f"<font color='#333333'>{num}</font>", styles["h2"])
    right_parts = [
        Paragraph(title, styles["step_title"]),
        Paragraph(desc,  styles["step_desc"]),
    ]
    t = Table([[left, right_parts]], colWidths=[0.45*inch, PAGE_W - 2*MARGIN - 0.45*inch - 0.2*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), SURFACE),
        ("BOX",        (0,0), (-1,-1), 0.5, BORDER),
        ("VALIGN",     (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING",   (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0), (-1,-1), 12),
    ]))
    return t

# ─── Resource row ────────────────────────────────────────────
def resource_row(icon, title, url_text, styles):
    left  = Paragraph(icon, styles["h3"])
    right = [Paragraph(title, styles["res_title"]), Paragraph(url_text, styles["res_url"])]
    t = Table([[left, right]], colWidths=[0.4*inch, PAGE_W - 2*MARGIN - 0.4*inch - 0.2*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), SURFACE),
        ("BOX",        (0,0), (-1,-1), 0.5, BORDER),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
    ]))
    return t

# ─────────────────────────────────────────────────────────────
#  CONNECTION 101 PDF
# ─────────────────────────────────────────────────────────────

def build_connection101():
    path = os.path.join(OUT_DIR, "connection-101.pdf")
    doc  = make_doc(path, "Connection 101  - Ask Anyway")
    s    = make_styles()
    story = []

    # Hero
    story += [
        Spacer(1, 0.2*inch),
        Paragraph("ASK ANYWAY  ·  FREE GUIDE", s["eyebrow"]),
        Paragraph("Connection 101", s["h1"]),
        Paragraph(
            "What to Say When You're Worried About Someone",
            s["h2"],
        ),
        Spacer(1, 6),
        Paragraph(
            "You've noticed something's off. This guide walks you through exactly "
            "what to say  - and what not to say. Written by a Licensed Clinical Social "
            "Worker and someone who lost a best friend to suicide.",
            s["body"],
        ),
        divider(),
    ]

    # Step 1
    story += [
        Paragraph("STEP 1", s["section_label"]),
        Paragraph("The Problem (You Already Know This One)", s["h2"]),
        Paragraph(
            "Your gut says something's wrong. And then your brain says: "
            "<b>What if I ask and make it worse? What if I say the wrong thing?</b>",
            s["body"],
        ),
        Paragraph(
            "So you don't ask. You tell yourself you'll bring it up later. Or you "
            "drop a vague text. Or you mention it to someone else.",
            s["body"],
        ),
        callout_box(
            "<b>Here's what we know:</b> In almost every case where someone dies by suicide, "
            "people around them saw warning signs they didn't know how to approach. "
            "Not because they didn't care. Because they didn't know <i>how</i>.",
            s,
        ),
        Spacer(1, 16),
    ]

    # Step 2
    story += [
        Paragraph("STEP 2", s["section_label"]),
        Paragraph("Why Being Indirect Doesn't Work", s["h2"]),
        Paragraph(
            "When we're scared, we soften the conversation. We ask "
            "<i>\"Are you okay?\"</i> and hope they'll volunteer the truth.",
            s["body"],
        ),
        Paragraph(
            "People who are struggling are expert at saying <b>\"I'm fine.\"</b> "
            "They've practiced it. It's the default away-message for pain. "
            "The indirect approach gives them an out. "
            "<b>You need to ask directly.</b>",
            s["body"],
        ),
        Spacer(1, 16),
    ]

    # Step 3
    story += [
        Paragraph("STEP 3", s["section_label"]),
        Paragraph("The Words  - Ready to Use", s["h2"]),

        Paragraph("OPENING THE DOOR", s["section_label"]),
    ]
    story.append(script_box([
        "__em__Find a private moment. Sit. Look at them.",
        '"I\'ve noticed you seem [different / withdrawn / not yourself] lately, '
        'and I care about you. I want to ask you something, and I need you to know '
        'I\'m asking because I care, not because I\'m judging. Can I ask you something real?"',
        "__em__Wait for them to nod or say yes.",
    ], s))

    story += [Spacer(1, 10), Paragraph("THE DIRECT ASK", s["section_label"])]
    story.append(script_box([
        '"Are you thinking about suicide?"',
        "__em__Or if that feels impossible:",
        '"Are you thinking about hurting yourself?"',
        '"Have you thought about ending your life?"',
    ], s))

    story += [Spacer(1, 10), Paragraph("IF THEY SAY YES", s["section_label"])]
    story.append(script_box([
        "__em__Your only job is to not end the conversation. Stay.",
        '"Thank you for telling me. I\'m really glad you did. I\'m not going anywhere. '
        'Can you tell me more about what\'s been going on?"',
        "__em__Then listen. Don't try to fix. Don't argue. Just listen and stay present.",
    ], s))
    story.append(Spacer(1, 20))

    # Step 4 - Do / Don't table
    story += [
        section_divider(),
        Paragraph("STEP 4", s["section_label"]),
        Paragraph("What Kills the Conversation", s["h2"]),
        Paragraph("Here's what NOT to say  - and why it backfires.", s["body"]),
        Spacer(1, 8),
    ]

    dd_data = [
        [Paragraph("DON'T SAY", s["section_label"]), Paragraph("WHAT ACTUALLY WORKS", s["section_label"])],
        [Paragraph('"You have so much to live for"', s["body"]),
         Paragraph('"Tell me what\'s been making you feel like this"', s["body"])],
        [Paragraph('"You should just talk to someone"', s["body"]),
         Paragraph('"I\'m here. Can we figure out support together?"', s["body"])],
        [Paragraph('"Other people have it worse"', s["body"]),
         Paragraph("Say nothing. Just listen.", s["body"])],
        [Paragraph('"I had no idea you felt this way"', s["body"]),
         Paragraph('"I\'m really glad you told me."', s["body"])],
        [Paragraph('"Promise me you won\'t do anything"', s["body"]),
         Paragraph('"I want to help you stay safe. Can we talk about that?"', s["body"])],
        [Paragraph('"Maybe you just need to think positive"', s["body"]),
         Paragraph("Stay silent and listen.", s["body"])],
    ]

    col_w = (PAGE_W - 2*MARGIN) / 2
    dd_table = Table(dd_data, colWidths=[col_w, col_w])
    dd_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0d0d0d")),
        ("BACKGROUND", (0, 1), (-1, -1), SURFACE),
        ("TEXTCOLOR",  (0, 1), (0, -1), HexColor("#c0786e")),
        ("TEXTCOLOR",  (1, 1), (1, -1), HexColor("#8eb898")),
        ("LINEBELOW",  (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEBEFORE", (1, 0), (1, -1), 0.5, BORDER),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("VALIGN",     (0,0), (-1,-1), "TOP"),
        ("BOX",        (0,0), (-1,-1), 0.5, BORDER),
    ]))
    story.append(dd_table)
    story.append(Spacer(1, 16))
    story.append(callout_box(
        "<b>The pattern:</b> The things that feel helpful are often the things that stop the conversation. "
        "The things that actually help are: staying present, validating their experience, and listening "
        "without trying to solve it immediately.",
        s,
    ))
    story.append(Spacer(1, 20))

    # Step 5
    story += [
        section_divider(),
        Paragraph("STEP 5", s["section_label"]),
        Paragraph("If They Confirm  - Your Next 3 Steps", s["h2"]),
        Spacer(1, 6),
        step_row("1", "Stay and listen  - don't transfer responsibility",
            "Your job is NOT to be their therapist. Your job is to not end the conversation and help "
            "them connect to professional support. Ask: \"How long have you been feeling this way? "
            "What's been happening?\" Let them talk.", s),
        Spacer(1, 8),
        step_row("2", "Understand how serious it is",
            "Ask: \"Do you have a plan for how you would do it?\" and \"Are you planning to act on "
            "this soon?\" Their answers tell you whether this is today-level or this-week-level urgency.", s),
        Spacer(1, 8),
        step_row("3", "Connect them to help  - together",
            "Don't just say \"call this number.\" If it's active crisis, call 988 together from your "
            "phone, or go to the nearest ER together. Don't leave them alone. If it's ongoing struggle, "
            "help them make the call or appointment. Check in tomorrow. Check in next week.", s),
        Spacer(1, 16),
    ]

    # Crisis block
    crisis_bg = HexColor("#0a0000")
    crisis_border = HexColor("#2a0a0a")
    crisis_data = [
        [Paragraph("IMMEDIATE SUPPORT  - 24/7, ALWAYS FREE", s["section_label"])],
        [Paragraph("📞  Call or text 988  - Suicide & Crisis Lifeline, real people", s["crisis"])],
        [Paragraph("💬  Text HOME to 741741  - Crisis Text Line, from anywhere", s["crisis"])],
        [Paragraph("🚑  Call 911 if someone is in immediate danger", s["crisis"])],
    ]
    ct = Table(crisis_data, colWidths=[PAGE_W - 2*MARGIN])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), crisis_bg),
        ("BOX",        (0,0), (-1,-1), 0.5, crisis_border),
        ("LINEBELOW",  (0,0), (0,0), 0.5, crisis_border),
        ("LEFTPADDING",  (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
    ]))
    story.append(ct)
    story.append(Spacer(1, 20))

    # Closing
    story += [
        section_divider(),
        Paragraph("CLOSING", s["section_label"]),
        Paragraph("You're Not Responsible for Saving Them", s["h2"]),
        Paragraph(
            "You asked. You stayed. You listened. You helped them connect to help. "
            "<b>That took courage.</b>",
            s["body"],
        ),
        Paragraph(
            "You are not responsible for making them better. Your job was to have a real "
            "conversation and help them connect to professional support. But your conversation mattered.",
            s["body"],
        ),
        Spacer(1, 16),
    ]

    # Resources
    story += [
        section_divider(),
        Paragraph("FREE RESOURCES", s["section_label"]),
        Paragraph("Always Available", s["h2"]),
        Spacer(1, 6),
        resource_row("📞", "988 Suicide & Crisis Lifeline", "Call or text 988  - 24/7, English and Spanish", s),
        Spacer(1, 6),
        resource_row("💬", "Crisis Text Line", "Text HOME to 741741  - 24/7, from anywhere", s),
        Spacer(1, 6),
        resource_row("🧠", "Psychology Today Therapist Finder", "psychologytoday.com  - filter by insurance, specialty, distance", s),
        Spacer(1, 6),
        resource_row("💛", "Open Path Collective", "openpathcollective.org  - low-cost therapy sessions", s),
        Spacer(1, 6),
        resource_row("🤝", "NAMI Helpline", "1-800-950-6264  - free support and referrals", s),
        Spacer(1, 24),
    ]

    # Disclaimer
    story.append(divider())
    story.append(Paragraph(
        "This guide is educational  - not therapy, not a diagnosis, and reading it doesn't create a clinical relationship. "
        "If you're in crisis, contact 988 (Suicide & Crisis Lifeline) by calling or texting 988, "
        "or text HOME to 741741 (Crisis Text Line), or call 911. | askaanyway.com",
        s["disclaimer"],
    ))

    doc.build(
        story,
        onFirstPage=make_canvas_fn("Ask Anyway  ·  Connection 101  ·  Free Guide  ·  988 Suicide & Crisis Lifeline available 24/7"),
        onLaterPages=make_canvas_fn("Ask Anyway  ·  Connection 101  ·  Free Guide  ·  988 Suicide & Crisis Lifeline available 24/7"),
    )
    print(f"✓ {path}")

# ─────────────────────────────────────────────────────────────
#  DAILY WELLBEING CHECKLIST PDF
# ─────────────────────────────────────────────────────────────

def build_checklist():
    path = os.path.join(OUT_DIR, "daily-checklist.pdf")
    doc  = make_doc(path, "Daily Wellbeing Checklist  - Ask Anyway")
    s    = make_styles()
    story = []

    # Hero
    story += [
        Spacer(1, 0.2 * inch),
        Paragraph("ASK ANYWAY  ·  FREE  ·  2-MINUTE CHECK-IN", s["eyebrow"]),
        Paragraph("Daily Wellbeing Checklist", s["h1"]),
        Paragraph("How are you actually doing today?", s["h2"]),
        Spacer(1, 4),
        Paragraph(
            "No sign-up. No tracking. Just an honest check-in with yourself. "
            "Check the boxes that are true right now. Take the full 2 minutes.",
            s["body"],
        ),
        Paragraph("Date: ___________________________________________", s["small"]),
        divider(),
    ]

    def check_section(label, items):
        rows = [Paragraph(label, s["check_section"])]
        for item in items:
            box_line = [
                Paragraph("□", s["h3"]),
                Paragraph(item, s["check_label"]),
            ]
            t = Table([box_line], colWidths=[0.35*inch, PAGE_W - 2*MARGIN - 0.35*inch - 0.1*inch])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), SURFACE),
                ("BOX",        (0,0), (-1,-1), 0.5, BORDER),
                ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
                ("LEFTPADDING",  (0,0), (-1,-1), 10),
                ("RIGHTPADDING", (0,0), (-1,-1), 10),
                ("TOPPADDING",   (0,0), (-1,-1), 9),
                ("BOTTOMPADDING",(0,0), (-1,-1), 9),
            ]))
            rows.append(t)
            rows.append(Spacer(1, 5))
        rows.append(Spacer(1, 12))
        return rows

    story += check_section("BODY", [
        "I slept at least 5 hours last night",
        "I've eaten something today (a real meal, not just coffee)",
        "I've had water today",
        "I've moved my body  - even a short walk counts",
    ])

    story += check_section("MIND", [
        "I'm not carrying something I haven't named yet",
        "My stress level feels manageable today (7 or below out of 10)",
        "I've been able to focus  - not stuck in loops or spiraling",
        "I'm not numbing out  - scrolling, drinking, or avoiding",
    ])

    story += check_section("CONNECTION", [
        "I've talked to at least one person today  - really talked",
        "I don't feel alone in what I'm carrying right now",
        "There's at least one person I could call right now if I needed to",
    ])

    story += check_section("MOOD", [
        "I feel like I belong somewhere or to someone today",
        "I have at least one thing I'm looking forward to  - even small",
        "I feel like I'm more than just surviving today",
    ])

    # Score guide
    story += [
        section_divider(),
        Paragraph("SCORE GUIDE", s["section_label"]),
        Paragraph("What to Make of Your Total", s["h2"]),
        Spacer(1, 8),
    ]

    score_data = [
        [Paragraph("0 – 3 checked", s["h3"]),
         Paragraph(
            "<b>Rough day.</b> Start with one: drink some water, text one person, or step outside 5 minutes. "
            "You don't have to fix everything today.", s["body"])],
        [Paragraph("4 – 6 checked", s["h3"]),
         Paragraph(
            "<b>Getting by.</b> Some things are holding, some aren't. Pick the one box you most want to "
            "check tomorrow and make a tiny plan.", s["body"])],
        [Paragraph("7 – 10 checked", s["h3"]),
         Paragraph(
            "<b>Doing okay.</b> More is working than not. Notice what you've kept up even when it's been hard. "
            "That's not nothing.", s["body"])],
        [Paragraph("11 – 13 checked", s["h3"]),
         Paragraph(
            "<b>Solid day.</b> What made today feel this way? Whatever it is  - try to protect that thing.", s["body"])],
        [Paragraph("14 – 15 checked", s["h3"]),
         Paragraph(
            "<b>Strong day.</b> You've put something in place that's working. Take a second to actually "
            "notice that before moving on.", s["body"])],
    ]

    col_a = 1.5 * inch
    col_b = PAGE_W - 2*MARGIN - col_a
    score_table = Table(score_data, colWidths=[col_a, col_b])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), SURFACE),
        ("LINEBELOW",  (0,0), (-1,-1), 0.5, BORDER),
        ("LINEBEFORE", (1,0), (1,-1), 0.5, BORDER),
        ("BOX",        (0,0), (-1,-1), 0.5, BORDER),
        ("TEXTCOLOR",  (0,0), (0,-1), HexColor("#84cc16")),
        ("VALIGN",     (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 20))

    # One thing box
    story += [
        section_divider(),
        Paragraph("ONE THING", s["section_label"]),
        Paragraph("What's one thing I can do today?", s["h2"]),
        Paragraph("Even something small counts.", s["body"]),
        Spacer(1, 8),
    ]
    write_box = Table(
        [[Paragraph("", s["body"])]],
        colWidths=[PAGE_W - 2*MARGIN],
        rowHeights=[0.9*inch],
    )
    write_box.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), SURFACE),
        ("BOX",        (0,0), (-1,-1), 0.5, BORDER),
        ("LEFTPADDING",  (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
    ]))
    story.append(write_box)
    story.append(Spacer(1, 20))

    # Crisis footer
    story += [
        section_divider(),
    ]
    ct_data = [
        [Paragraph("IF YOU'RE STRUGGLING RIGHT NOW", s["section_label"])],
        [Paragraph(
            "Call or text 988  - Suicide & Crisis Lifeline  - 24/7, free, real people.\n"
            "Text HOME to 741741  - Crisis Text Line  - text from anywhere, right now.\n"
            "Call 911 if you or someone else is in immediate danger.",
            s["crisis"]
        )],
    ]
    ct = Table(ct_data, colWidths=[PAGE_W - 2*MARGIN])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), HexColor("#0a0000")),
        ("BOX",        (0,0), (-1,-1), 0.5, HexColor("#2a0a0a")),
        ("LEFTPADDING",  (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
    ]))
    story.append(ct)
    story.append(Spacer(1, 16))

    story.append(divider())
    story.append(Paragraph(
        "This checklist is for personal reflection  - not therapy, not a diagnosis. "
        "If you're in crisis, contact 988 or text HOME to 741741. | askanyway.com",
        s["disclaimer"],
    ))

    doc.build(
        story,
        onFirstPage=make_canvas_fn("Ask Anyway  ·  Daily Wellbeing Checklist  ·  Free  ·  988 Suicide & Crisis Lifeline available 24/7"),
        onLaterPages=make_canvas_fn("Ask Anyway  ·  Daily Wellbeing Checklist  ·  Free  ·  988 Suicide & Crisis Lifeline available 24/7"),
    )
    print(f"✓ {path}")


if __name__ == "__main__":
    build_connection101()
    build_checklist()
    print("\nBoth PDFs ready in ask-anyway-deploy/guides/")
