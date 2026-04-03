"""
Build branded PDFs from markdown guide / worksheet files.

Usage:
    python3 scripts/build_pdf.py <file.md>            # single file
    python3 scripts/build_pdf.py --all-guides          # all audience-slant guides
    python3 scripts/build_pdf.py --all-worksheets      # all worksheets
    python3 scripts/build_pdf.py --all                 # everything
    python3 scripts/build_pdf.py --html <file.md>      # dump HTML for debugging

Requires: playwright, markdown  (pip install playwright markdown)
          python3 -m playwright install chromium
"""

import argparse
import re
import sys
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output" / "pdf"

# ---------------------------------------------------------------------------
# Brand constants
# ---------------------------------------------------------------------------
TEAL       = "#1a6b6a"
TEAL_DARK  = "#0f4e4d"
AMBER      = "#d4922a"
AMBER_LIGHT = "#e8a840"
WARM_WHITE = "#faf7f2"
CHARCOAL   = "#2d2d2d"

# Page dimensions (Letter) used by CSS
PAGE_W = "8.5in"
PAGE_H = "11in"
MARGIN_V = "0.65in"
MARGIN_H = "0.75in"

FONTS_URL = "https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&family=Raleway:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap"

# ---------------------------------------------------------------------------
# CSS — all layout controlled here; Playwright margins are set to 0
# ---------------------------------------------------------------------------
CSS = f"""
@page {{ size: letter; margin: 0; }}

*, *::before, *::after {{ box-sizing: border-box; }}

body {{
    font-family: 'Raleway', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-weight: 400;
    font-size: 10.5pt;
    line-height: 1.7;
    color: {CHARCOAL};
    margin: 0;
    padding: 0;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}

/* ───────────── Cover ───────────── */
.cover {{
    width: {PAGE_W};
    height: {PAGE_H};
    background: {WARM_WHITE};
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    page-break-after: always;
    overflow: hidden;
}}

.cover-logo {{
    width: 140px;
    height: 140px;
    border-radius: 50%;
    border: 1px solid {TEAL};
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin-bottom: 32px;
    flex-shrink: 0;
}}
.cover-logo .logo-the {{
    font-family: 'Raleway', sans-serif;
    font-weight: 400;
    font-size: 6.5pt;
    letter-spacing: 3.5pt;
    text-transform: uppercase;
    color: {TEAL};
}}
.cover-logo .logo-ask {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 900;
    font-size: 24pt;
    text-transform: uppercase;
    color: {TEAL};
    line-height: 1.05;
    letter-spacing: -0.5pt;
}}
.cover-logo .logo-anyway {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 900;
    font-size: 24pt;
    text-transform: uppercase;
    color: {AMBER};
    line-height: 1.05;
    letter-spacing: -0.5pt;
}}
.cover-logo .logo-line {{
    width: 28px;
    height: 1.5px;
    background: {AMBER};
    margin: 4px 0;
}}
.cover-logo .logo-campaign {{
    font-family: 'Raleway', sans-serif;
    font-weight: 500;
    font-size: 5.5pt;
    letter-spacing: 3.5pt;
    text-transform: uppercase;
    color: {TEAL};
}}

.cover-title {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 800;
    font-size: 22pt;
    color: {TEAL};
    line-height: 1.25;
    margin: 0 1.2in 10px 1.2in;
    max-width: 5.5in;
}}
.cover-bar {{
    width: 48px;
    height: 2px;
    background: {AMBER};
    margin: 14px auto;
}}
.cover-audience {{
    font-family: 'Raleway', sans-serif;
    font-weight: 500;
    font-size: 10pt;
    letter-spacing: 2.5pt;
    text-transform: uppercase;
    color: {AMBER};
    margin-bottom: 18px;
}}
.cover-type {{
    font-family: 'Raleway', sans-serif;
    font-weight: 400;
    font-size: 8.5pt;
    color: #999;
    letter-spacing: 1.5pt;
    text-transform: uppercase;
}}
.cover-from {{
    font-family: 'Raleway', sans-serif;
    font-style: italic;
    font-size: 9pt;
    color: #999;
    margin-top: 8px;
}}
.cover-disclaimer {{
    font-family: 'Raleway', sans-serif;
    font-size: 7pt;
    color: #aaa;
    position: absolute;
    bottom: 28px;
    left: 0;
    right: 0;
    text-align: center;
}}
.cover {{
    position: relative;
}}

/* ───────────── Content pages ───────────── */
.content {{
    padding: {MARGIN_V} {MARGIN_H};
}}

.content h1 {{ display: none; }}

.content h2 {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    font-size: 13pt;
    color: {TEAL};
    margin: 20pt 0 6pt 0;
    padding-bottom: 3pt;
    border-bottom: 1.5px solid {AMBER};
    line-height: 1.35;
    page-break-after: avoid;
}}

.content h2:first-child {{
    margin-top: 0;
}}

.content h3 {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 600;
    font-size: 11pt;
    color: {TEAL_DARK};
    margin: 14pt 0 4pt 0;
    page-break-after: avoid;
}}

.content p  {{ margin: 0 0 8pt 0; }}
.content ol {{ margin: 0 0 10pt 22pt; }}
.content ul {{ margin: 0 0 10pt 22pt; }}
.content li {{ margin-bottom: 4pt; }}
.content strong {{ font-weight: 600; }}
.content em {{ font-style: italic; color: #555; }}
.content blockquote {{
    border-left: 3px solid {TEAL};
    margin: 10pt 0;
    padding: 8pt 14pt;
    color: #555;
    font-size: 9.5pt;
    background: #f9f8f5;
    border-radius: 0 4px 4px 0;
}}

/* ── Worksheet sections inside guides ── */
.worksheet-section {{
    background: #f4f1ec;
    border-left: 3px solid {AMBER};
    padding: 12pt 16pt 8pt 16pt;
    margin: 18pt 0;
    border-radius: 0 6px 6px 0;
    page-break-before: always;
    page-break-inside: avoid;
}}
.worksheet-section h2 {{
    border-bottom: none;
    margin-top: 0;
    padding-bottom: 0;
    color: {AMBER};
    font-size: 12pt;
}}
.worksheet-section .ws-goal {{
    font-style: italic;
    color: {TEAL_DARK};
    font-size: 10pt;
    margin-bottom: 8pt;
}}
.worksheet-section ul {{
    list-style: none;
    margin-left: 0;
    padding-left: 0;
}}
.worksheet-section li {{
    padding: 8pt 0 4pt 0;
    margin-bottom: 0;
    line-height: 1.5;
}}
.worksheet-section li .writing-lines {{
    margin-top: 6pt;
    border-bottom: 1px solid #ccc;
    height: 24pt;
}}
.worksheet-section li .writing-lines + .writing-lines {{
    border-bottom: 1px solid #ddd;
}}

/* ── Standalone worksheet body ── */
.worksheet-standalone .ws-goal {{
    font-family: 'Raleway', sans-serif;
    font-style: italic;
    font-size: 10.5pt;
    color: {TEAL};
    margin-bottom: 14pt;
    padding-bottom: 8pt;
    border-bottom: 1px solid #ddd;
}}
.worksheet-standalone ul {{
    list-style: none;
    margin: 0;
    padding: 0;
}}
.worksheet-standalone li {{
    padding: 10pt 0 4pt 0;
    margin-bottom: 0;
    line-height: 1.5;
}}
.worksheet-standalone li .writing-lines {{
    margin-top: 6pt;
    border-bottom: 1px solid #d4d0ca;
    height: 26pt;
}}
.worksheet-standalone li .writing-lines:last-child {{
    margin-bottom: 8pt;
}}

/* ── Crisis footer ── */
.crisis-footer {{
    margin-top: 28pt;
    padding-top: 12pt;
    border-top: 1px solid #ddd;
    page-break-inside: avoid;
}}
.crisis-footer .note {{
    font-size: 8.5pt;
    color: #888;
    line-height: 1.55;
    margin-bottom: 8pt;
}}
.crisis-box {{
    background: {WARM_WHITE};
    border: 1px solid {TEAL};
    border-radius: 5px;
    padding: 10pt 12pt;
}}
.crisis-box p {{
    font-size: 8.5pt;
    color: {TEAL_DARK};
    margin: 0 0 3pt 0;
    line-height: 1.5;
}}
.crisis-box p:last-child {{ margin-bottom: 0; }}
.crisis-box strong {{ color: {TEAL}; font-weight: 600; }}

/* ───────────── Back page ───────────── */
.back-page {{
    width: {PAGE_W};
    height: {PAGE_H};
    page-break-before: always;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    overflow: hidden;
    position: relative;
}}
.back-logo {{
    width: 140px;
    height: 140px;
    border-radius: 50%;
    border: 1px solid {TEAL};
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin-bottom: 28px;
}}
.back-logo .logo-the {{
    font-family: 'Raleway', sans-serif;
    font-weight: 400;
    font-size: 6.5pt;
    letter-spacing: 3.5pt;
    text-transform: uppercase;
    color: {TEAL};
}}
.back-logo .logo-ask {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 900;
    font-size: 24pt;
    text-transform: uppercase;
    color: {TEAL};
    line-height: 1.05;
    letter-spacing: -0.5pt;
}}
.back-logo .logo-anyway {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 900;
    font-size: 24pt;
    text-transform: uppercase;
    color: {AMBER};
    line-height: 1.05;
    letter-spacing: -0.5pt;
}}
.back-logo .logo-line {{
    width: 28px;
    height: 1.5px;
    background: {AMBER};
    margin: 4px 0;
}}
.back-logo .logo-campaign {{
    font-family: 'Raleway', sans-serif;
    font-weight: 500;
    font-size: 5.5pt;
    letter-spacing: 3.5pt;
    text-transform: uppercase;
    color: {TEAL};
}}

.back-tagline {{
    font-family: 'Raleway', sans-serif;
    font-weight: 400;
    font-size: 10pt;
    color: #999;
    margin-bottom: 28px;
    font-style: italic;
}}
.back-crisis {{
    font-family: 'Raleway', sans-serif;
    font-size: 8.5pt;
    color: {TEAL};
    line-height: 1.9;
}}
.back-crisis strong {{ color: {TEAL}; }}

.back-disclaimer {{
    position: absolute;
    bottom: 28px;
    left: 0.75in;
    right: 0.75in;
    text-align: center;
}}
.back-disclaimer p {{
    font-family: 'Raleway', sans-serif;
    font-size: 6.5pt;
    color: #aaa;
    line-height: 1.6;
    margin: 0 0 3pt 0;
}}
.back-disclaimer p:last-child {{ margin-bottom: 0; }}
"""

LOGO_HTML = """<div class="logo-the">THE</div>
<div class="logo-ask">ASK</div>
<div class="logo-anyway">ANYWAY</div>
<div class="logo-line"></div>
<div class="logo-campaign">CAMPAIGN</div>"""

CRISIS_BOX_HTML = """<div class="crisis-box">
<p><strong>988 Suicide &amp; Crisis Lifeline:</strong> call or text <strong>988</strong></p>
<p><strong>Crisis Text Line:</strong> text <strong>HOME</strong> to <strong>741741</strong></p>
<p>If you or someone you know is in immediate danger, call <strong>911</strong>.</p>
</div>"""

BACK_PAGE_HTML = f"""<div class="back-page">
<div class="back-logo">{LOGO_HTML}</div>
<div class="back-tagline">You don&rsquo;t need the perfect words. You just need to ask.</div>
<div class="back-crisis">
<strong>988 Suicide &amp; Crisis Lifeline:</strong> call or text 988<br>
<strong>Crisis Text Line:</strong> text HOME to 741741<br>
<strong>Emergency:</strong> call 911
</div>
<div class="back-disclaimer">
<p>This material is for educational purposes only. It is not therapy, not a clinical diagnosis, and does not replace professional mental health support.</p>
<p>The author and publisher disclaim any liability for actions taken or not taken based on this content. Individual results may vary.</p>
<p>&copy; The Ask Anyway Campaign. All rights reserved.</p>
</div>
</div>"""

# Disclaimer text is now merged into BACK_PAGE_HTML


# ---------------------------------------------------------------------------
# Markdown parsing helpers
# ---------------------------------------------------------------------------

METADATA_KEYS = {
    "Status", "Guide ID", "Guide type", "Source", "Batch",
    "Priority", "Audience Bucket", "Audience Tier", "Base Guide Path",
}


def parse_markdown_file(path: Path):
    """Extract title, metadata dict, and body text from a markdown file."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    title = ""
    metadata = {}
    body_lines = []
    in_metadata = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("# ") and not title:
            title = stripped[2:].strip()
            in_metadata = True
            continue

        if in_metadata:
            m = re.match(r'^([A-Za-z][A-Za-z /]+):\s*(.+)$', stripped)
            if m and m.group(1) in METADATA_KEYS:
                metadata[m.group(1)] = m.group(2).strip()
                continue
            if stripped == "":
                continue
            in_metadata = False

        body_lines.append(line)

    return title, metadata, "\n".join(body_lines)


def is_worksheet_file(path: Path) -> bool:
    return "/worksheets/" in str(path)


def _fix_md_lists(text: str) -> str:
    """Ensure a blank line appears before bullet/numbered lists so the
    markdown parser recognises them (Python-Markdown requires it)."""
    out = []
    prev = ""
    for line in text.split("\n"):
        stripped = line.strip()
        is_list = bool(re.match(r'^[-*+] |^\d+\. ', stripped))
        prev_blank = prev.strip() == ""
        prev_list = bool(re.match(r'^[-*+] |^\d+\. ', prev.strip()))
        if is_list and not prev_blank and not prev_list:
            out.append("")           # insert blank line
        out.append(line)
        prev = line
    return "\n".join(out)


def _strip_em_dashes(text: str) -> str:
    """Remove all em dashes (Unicode and HTML entity), replacing with commas."""
    # Spaced em dash (" — ") → comma
    text = text.replace(" \u2014 ", ", ")
    # No-space em dash ("word—word") → comma+space
    text = text.replace("\u2014", ", ")
    # HTML entity variants
    text = text.replace(" &mdash; ", ", ")
    text = text.replace("&mdash;", ", ")
    # Clean up any resulting double commas or comma-after-comma
    text = text.replace(",,", ",")
    # Clean up double spaces
    while "  " in text:
        text = text.replace("  ", " ")
    return text


def md_to_html(text: str) -> str:
    html = markdown.markdown(_fix_md_lists(text), extensions=["extra"])
    return _strip_em_dashes(html)


def split_body_sections(body_text: str):
    """Split guide body into (pre_worksheet, [worksheet_texts], footer)."""
    # Strip footer (everything from --- + "A quick note")
    footer_pat = r'\n---\s*\n+\*\*A quick note:\*\*'
    parts = re.split(footer_pat, body_text, maxsplit=1)
    main = parts[0]
    footer = parts[1] if len(parts) > 1 else ""

    # Find worksheet sections
    ws_pat = r'(## Worksheet \d+:.*?)(?=## Worksheet \d+:|$)'
    matches = list(re.finditer(ws_pat, main, re.DOTALL))
    if matches:
        pre = main[:matches[0].start()].strip()
        worksheets = [m.group(1).strip() for m in matches]
    else:
        pre = main.strip()
        worksheets = []

    return pre, worksheets, footer.strip()


def _parse_worksheet_md(ws_text: str):
    """Parse a single worksheet markdown block into (heading, goal, prompts_html)."""
    lines = ws_text.split("\n")
    heading = ""
    goal = ""
    prompt_lines = []

    for line in lines:
        s = line.strip()
        if s.startswith("## "):
            heading = _strip_em_dashes(s[3:].strip())
        elif s.lower().startswith("goal:"):
            goal = _strip_em_dashes(s.split(":", 1)[1].strip())
        elif s.lower().startswith("prompts:"):
            continue   # skip label
        elif s.startswith("- "):
            prompt_lines.append(_strip_em_dashes(s[2:].strip()))
        # other lines (blank, etc.) ignored

    GUIDE_WS_LINES = 3  # ruled lines per prompt in guide worksheets
    lines_html = '<div class="writing-lines"></div>' * GUIDE_WS_LINES
    prompts_html = "\n".join(
        f"<li>{p}{lines_html}</li>"
        for p in prompt_lines
    )
    return heading, goal, f"<ul>\n{prompts_html}\n</ul>"


def _html_doc(title, inner_html):
    """Wrap inner HTML in a full document with fonts + CSS."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link rel="stylesheet" href="{FONTS_URL}">
<style>{CSS}</style>
</head>
<body>
{inner_html}
</body>
</html>"""


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

def build_guide_html(title, metadata, body_text):
    audience = metadata.get("Audience Bucket", "")
    guide_type = metadata.get("Guide type", "guide").title()

    pre_ws, worksheets, footer = split_body_sections(body_text)

    body_html = md_to_html(pre_ws)

    # Build worksheet boxes (parsed explicitly so prompts render as lists)
    ws_blocks = ""
    for ws_md in worksheets:
        heading, goal, prompts_html = _parse_worksheet_md(ws_md)
        ws_blocks += f"""<div class="worksheet-section">
<h2>{heading}</h2>
{"<p class='ws-goal'>" + goal + "</p>" if goal else ""}
{prompts_html}
</div>
"""

    cover = f"""<div class="cover">
<div class="cover-logo">{LOGO_HTML}</div>
<div class="cover-title">{title}</div>
<div class="cover-bar"></div>
{"<div class='cover-audience'>" + audience + "</div>" if audience else ""}
<div class="cover-type">{guide_type} Guide</div>
<div class="cover-disclaimer">For educational purposes only. Not a substitute for professional mental health support.</div>
</div>"""

    inner = f"""{cover}
<div class="content">
{body_html}
{ws_blocks}
</div>
{BACK_PAGE_HTML}"""

    return _html_doc(title, inner)


def build_worksheet_html(title, metadata, body_text):
    audience = ""
    m = re.search(r'\*\*Audience:\*\*\s*(.+)', body_text)
    if m:
        audience = m.group(1).strip()

    from_guide = ""
    m = re.search(r'\*\*From guide:\*\*\s*(.+)', body_text)
    if m:
        from_guide = m.group(1).strip()

    # Extract goal + prompt items
    goal = ""
    prompts = []
    for line in body_text.split("\n"):
        s = line.strip()
        if s.startswith("**Audience:") or s.startswith("**From guide:"):
            continue
        if s == "---":
            continue
        if s.startswith("**A quick note:"):
            break
        if s.lower().startswith("goal:"):
            goal = _strip_em_dashes(s.split(":", 1)[1].strip())
        elif s.lower().startswith("prompts:"):
            continue
        elif s.startswith("- "):
            prompts.append(_strip_em_dashes(s[2:].strip()))

    STANDALONE_WS_LINES = 4  # ruled lines per prompt in standalone worksheets
    lines_html = '<div class="writing-lines"></div>' * STANDALONE_WS_LINES
    prompts_html = "\n".join(
        f"<li>{p}{lines_html}</li>"
        for p in prompts
    )

    cover = f"""<div class="cover">
<div class="cover-logo">{LOGO_HTML}</div>
<div class="cover-title">{title}</div>
<div class="cover-bar"></div>
{"<div class='cover-audience'>" + audience + "</div>" if audience else ""}
<div class="cover-type">Worksheet</div>
{"<div class='cover-from'>From: " + from_guide + "</div>" if from_guide else ""}
<div class="cover-disclaimer">For educational purposes only. Not a substitute for professional mental health support.</div>
</div>"""

    inner = f"""{cover}
<div class="content worksheet-standalone">
{"<p class='ws-goal'>" + goal + "</p>" if goal else ""}
<ul>
{prompts_html}
</ul>
</div>
{BACK_PAGE_HTML}"""

    return _html_doc(title, inner)


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def generate_pdf(page, md_path: Path, out_dir: Path):
    title, metadata, body_text = parse_markdown_file(md_path)

    if is_worksheet_file(md_path):
        html_str = build_worksheet_html(title, metadata, body_text)
    else:
        html_str = build_guide_html(title, metadata, body_text)

    rel = md_path.relative_to(ROOT / "content")
    pdf_path = out_dir / rel.with_suffix(".pdf")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    page.set_content(html_str, wait_until="networkidle")
    page.pdf(
        path=str(pdf_path),
        format="Letter",
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        print_background=True,
    )
    return pdf_path


def collect_files(mode: str):
    files = []
    if mode in ("all", "guides"):
        d = ROOT / "content" / "topic-guides" / "audience-slants"
        if d.exists():
            files.extend(sorted(d.rglob("*.md")))
    if mode in ("all", "worksheets"):
        d = ROOT / "content" / "worksheets"
        if d.exists():
            files.extend(sorted(d.rglob("*.md")))
    if mode == "base_guides":
        for sub in ("chapters", "splits", "new-topics"):
            d = ROOT / "content" / "topic-guides" / sub
            if d.exists():
                files.extend(sorted(d.glob("*.md")))
    return files


def main():
    ap = argparse.ArgumentParser(description="Build branded PDFs from markdown")
    ap.add_argument("file", nargs="?", help="Single markdown file to convert")
    ap.add_argument("--all-guides", action="store_true")
    ap.add_argument("--all-worksheets", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--base-guides", action="store_true",
                     help="Build only the 79 base topic guides (no audience slants)")
    ap.add_argument("--html", action="store_true",
                     help="Dump HTML to output/ instead of PDF (debug)")
    ap.add_argument("--output", "-o", default=str(OUTPUT_DIR))
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.file:
        files = [Path(args.file).resolve()]
    elif args.all:
        files = collect_files("all")
    elif args.base_guides:
        files = collect_files("base_guides")
    elif args.all_guides:
        files = collect_files("guides")
    elif args.all_worksheets:
        files = collect_files("worksheets")
    else:
        ap.print_help()
        sys.exit(1)

    # HTML-only debug mode
    if args.html:
        for f in files:
            title, meta, body = parse_markdown_file(f)
            if is_worksheet_file(f):
                html = build_worksheet_html(title, meta, body)
            else:
                html = build_guide_html(title, meta, body)
            out = out_dir / f.with_suffix(".html").name
            out.write_text(html, encoding="utf-8")
            print(f"  HTML → {out}")
        return

    total = len(files)
    errors = 0
    print(f"Building {total} PDF(s)…")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for i, f in enumerate(files, 1):
            if not f.exists():
                print(f"  ✗ Not found: {f}")
                errors += 1
                continue
            try:
                pdf = generate_pdf(page, f, out_dir)
                if total == 1 or i % 50 == 0 or i == total:
                    print(f"  [{i}/{total}] ✓ {pdf.name}")
            except Exception as e:
                errors += 1
                print(f"  [{i}/{total}] ✗ {f.name}: {e}")

        browser.close()

    print(f"\nDone: {total - errors} succeeded, {errors} errors")


if __name__ == "__main__":
    main()
