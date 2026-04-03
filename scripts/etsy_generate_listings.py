#!/usr/bin/env python3
"""
Generate Etsy listing data (title, description, tags, price) for all 79 base guides.

Reads:
  - quiz/base-guide-catalog.json  (metadata, tags, domain, cluster)
  - content/topic-guides/*/        (markdown body for descriptions)

Outputs:
  - output/etsy/listings.json      (review/edit before uploading)

Usage:
  python3 scripts/etsy_generate_listings.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "quiz" / "base-guide-catalog.json"
OUTPUT = ROOT / "output" / "etsy" / "listings.json"
PRICE = 6.99

# ---------------------------------------------------------------------------
# Tag generation helpers
# ---------------------------------------------------------------------------

# Universal tags included on every listing (max 20 chars each)
UNIVERSAL_TAGS = [
    "mental health",
    "self help guide",
    "digital download",
    "pdf guide",
    "coping skills",
    "wellness",
]

# Map catalog domains to human-readable Etsy tags
DOMAIN_TAGS = {
    "nervous_system_mood_cognition": ["anxiety help", "mood support"],
    "sleep_body_pain_substances": ["sleep help", "pain management"],
    "relationships_family_parenting": ["relationships", "family support"],
    "intimacy_sex_connection": ["intimacy guide", "couples help"],
    "moral_injury_guilt_shame_spirituality": ["moral injury", "guilt and shame"],
    "work_identity_transition": ["career change", "life transition"],
    "dopamine_habits_addictions": ["addiction help", "bad habits"],
    "gap_or_custom": ["self care", "personal growth"],
}

# Map catalog clusters to tags
CLUSTER_TAGS = {
    "reactivity": "emotional control",
    "general": "self improvement",
    "crisis": "crisis support",
    "sleep": "insomnia help",
    "body": "body awareness",
    "intimacy": "intimacy",
    "moral": "shame recovery",
    "relationship": "relationship help",
    "work": "work stress",
    "habit": "habit change",
}


def _clean_tag(raw: str) -> str:
    """Convert a catalog snake_case tag to an Etsy-friendly tag (max 20 chars)."""
    t = raw.replace("_", " ").strip()
    # Etsy tags: letters, numbers, whitespace, -, ', TM, (C), (R) only
    t = re.sub(r"[^\w\s\-']", "", t)
    return t[:20]


def build_tags(guide: dict) -> list:
    """Build up to 13 Etsy tags for a guide from its metadata."""
    tags = list(UNIVERSAL_TAGS)  # start with 6 universals

    # Add catalog-specific tags (up to 3)
    for raw in guide.get("tags", []):
        tag = _clean_tag(raw)
        if tag and tag not in tags and len(tag) <= 20:
            tags.append(tag)

    # Add domain tags
    domain = guide.get("domain", "")
    for dt in DOMAIN_TAGS.get(domain, []):
        if dt not in tags:
            tags.append(dt)

    # Add cluster tag
    cluster = guide.get("cluster", "")
    ct = CLUSTER_TAGS.get(cluster, "")
    if ct and ct not in tags:
        tags.append(ct)

    # Cap at 13
    return tags[:13]


# ---------------------------------------------------------------------------
# Description extraction
# ---------------------------------------------------------------------------

def extract_what_this_helps_with(md_path: Path) -> str:
    """Pull the 'What This Helps With' section text from a guide markdown file."""
    text = md_path.read_text(encoding="utf-8")
    match = re.search(
        r'## What This Helps With\s*\n(.*?)(?=\n## |\Z)',
        text, re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return ""


def build_description(guide: dict, hook: str) -> str:
    """Build a full Etsy listing description for a guide."""
    title = guide["title"]

    desc = f"""{title}

{hook}

WHAT'S INCLUDED
- Practical guide with actionable steps (not theory - real strategies that work)
- 2 printable worksheets to track your progress
- Immediate digital download - start right now

WHAT'S INSIDE
- What's actually happening (clear, no-jargon explanation)
- What to do right now (step-by-step actions you can take today)
- What to say (exact words and phrases you can use)
- Common mistakes to avoid
- Your 24-hour action plan
- 2 hands-on worksheets with writing prompts

FROM THE ASK ANYWAY CAMPAIGN
Created by a licensed clinical social worker (LCSW) and loss survivor. Warm, direct, real-talk style. No clinical jargon, no academic fluff. Just what actually helps.

HOW IT WORKS
1. Purchase and download instantly
2. Open the PDF on any device or print it out
3. Read through the guide (takes about 15 minutes)
4. Complete the worksheets at your own pace
5. Use the 24-hour action plan to start making changes today

IMPORTANT NOTE
This guide is for educational purposes only. It is not therapy, not a clinical diagnosis, and does not replace professional mental health support.

If you or someone you know is in crisis:
- 988 Suicide and Crisis Lifeline: call or text 988
- Crisis Text Line: text HOME to 741741
- Emergency: call 911"""

    return desc


def build_title(guide: dict) -> str:
    """Build an Etsy-optimized title (max 140 chars, only one + allowed)."""
    base = guide["title"]
    has_plus = "+" in base

    # If title already has +, use & in suffix to stay under Etsy's 1-plus rule
    if has_plus:
        suffix = " - Mental Health Guide and Worksheets - Digital Download PDF"
    else:
        suffix = " - Mental Health Guide + Worksheets - Digital Download PDF"

    full = base + suffix
    if len(full) <= 140:
        return full
    # Try shorter suffix
    suffix2 = " - Mental Health Guide and Worksheets - PDF" if has_plus else " - Mental Health Guide + Worksheets - PDF"
    full2 = base + suffix2
    if len(full2) <= 140:
        return full2
    # Last resort: just title + minimal suffix
    return (base + " - Mental Health Guide PDF")[:140]


# ---------------------------------------------------------------------------
# PDF path resolution
# ---------------------------------------------------------------------------

def resolve_pdf_path(guide: dict) -> str:
    """Resolve the PDF path in output/etsy/ for this guide."""
    base_path = guide["base_path"]  # e.g. content/topic-guides/chapters/ch-01-xxx.md
    rel = base_path.replace("content/", "", 1)
    pdf_rel = re.sub(r'\.md$', '.pdf', rel)
    return f"output/etsy/{pdf_rel}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    guides = catalog["guides"]

    listings = []
    missing = []

    for guide in guides:
        md_path = ROOT / guide["base_path"]
        if not md_path.exists():
            missing.append(guide["guide_id"])
            continue

        hook = extract_what_this_helps_with(md_path)
        title = build_title(guide)
        description = build_description(guide, hook)
        tags = build_tags(guide)
        pdf_path = resolve_pdf_path(guide)

        # Verify PDF exists
        full_pdf = ROOT / pdf_path
        if not full_pdf.exists():
            print(f"  WARNING: PDF not found: {pdf_path}")

        listing = {
            "guide_id": guide["guide_id"],
            "title": title,
            "description": description,
            "tags": tags,
            "price": PRICE,
            "pdf_path": pdf_path,
            "who_made": "i_did",
            "when_made": "2020_2026",
            "is_supply": False,
            "type": "download",
            "quantity": 999,
        }
        listings.append(listing)

    # Write output
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"listings": listings, "count": len(listings)}, indent=2),
        encoding="utf-8"
    )

    print(f"Generated {len(listings)} listings -> {OUTPUT}")
    if missing:
        print(f"  Missing source files: {missing}")

    # Summary stats
    title_lens = [len(l["title"]) for l in listings]
    tag_counts = [len(l["tags"]) for l in listings]
    print(f"  Title lengths: {min(title_lens)}-{max(title_lens)} chars (max 140)")
    print(f"  Tags per listing: {min(tag_counts)}-{max(tag_counts)} (max 13)")
    print(f"  Price: ${PRICE}")


if __name__ == "__main__":
    main()
