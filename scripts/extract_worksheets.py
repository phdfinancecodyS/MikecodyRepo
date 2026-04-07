#!/usr/bin/env python3
"""
Extract standalone worksheets from all 1,343 audience-variant guides.
Creates 2 worksheets per guide (Pattern Finder + Action Builder) = 2,686 files.
Also audits whether each worksheet is actually topic-relevant.
"""
import os, glob, re

SRC = "content/topic-guides/audience-slants"
DEST = "content/worksheets"

DISCLAIMER = """
---

**A quick note:** This worksheet is educational  - it's not therapy, it's not a diagnosis, and using it doesn't create a clinical relationship between us. It's built to help you take the next step, not replace professional support. If you're in crisis, contact 988 (Suicide & Crisis Lifeline), text HOME to 741741 (Crisis Text Line), or call 911.
"""

stats = {"created": 0, "skipped": 0, "generic_w1": 0, "generic_w2": 0, "errors": []}


def extract_metadata(content):
    """Pull title and audience from file content."""
    title = None
    audience = None
    for line in content.split("\n"):
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        if line.startswith("Audience Bucket:"):
            audience = line.split(":", 1)[1].strip()
        if title and audience:
            break
    return title, audience


def extract_worksheet(content, ws_num):
    """Extract a specific worksheet section from the guide content by number prefix."""
    prefix = f"## Worksheet {ws_num}:"
    idx = content.find(prefix)
    if idx == -1:
        return None, None

    # Extract the full header line to get the worksheet name
    header_end = content.index("\n", idx)
    header_line = content[idx:header_end].strip()
    ws_name = header_line[len(f"## Worksheet {ws_num}: "):].strip()

    after = content[header_end:]

    # Find the end: next ## header, or --- divider, or end of file
    end_markers = []
    next_section = after.find("\n## ")
    next_divider = after.find("\n---")
    if next_section != -1:
        end_markers.append(next_section)
    if next_divider != -1:
        end_markers.append(next_divider)

    if end_markers:
        end = min(end_markers)
        body = after[:end].strip()
    else:
        body = after.strip()

    return body, ws_name


def check_generic(body, title):
    """Check if worksheet prompts are generic (contain boilerplate patterns)."""
    generic_markers = [
        "What happened right before it started?",
        "What thought pattern showed up at the same time?",
        "Earliest warning sign I can catch next time:",
        "Script I'll use word-for-word next time:",
        f'when did "{title}" show up most',
    ]
    for marker in generic_markers:
        if marker.lower() in body.lower():
            return True
    return False


def build_worksheet_file(title, audience, ws_num, ws_name, body):
    """Build a standalone worksheet markdown file."""
    out = f"# {title}  - {ws_name}\n\n"
    out += f"**Audience:** {audience}\n\n"
    out += f"**From guide:** {title}\n\n"
    out += "---\n\n"
    out += body + "\n"
    out += DISCLAIMER
    return out


def slugify(text):
    """Convert text to filename-safe slug."""
    s = text.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


def process_file(fpath):
    with open(fpath) as f:
        content = f.read()

    title, audience = extract_metadata(content)
    if not title or not audience:
        stats["errors"].append(f"Missing metadata: {fpath}")
        return

    # Get the guide filename stem for naming
    basename = os.path.splitext(os.path.basename(fpath))[0]
    audience_slug = slugify(audience)

    # Create audience subdirectory
    audience_dir = os.path.join(DEST, audience_slug)
    os.makedirs(audience_dir, exist_ok=True)

    for ws_num in [1, 2]:
        body, ws_name = extract_worksheet(content, ws_num)
        if not body:
            stats["errors"].append(f"No Worksheet {ws_num} found: {fpath}")
            continue

        # Check for generic content
        is_generic = check_generic(body, title)
        if is_generic:
            if ws_num == 1:
                stats["generic_w1"] += 1
            else:
                stats["generic_w2"] += 1

        # Build output
        ws_content = build_worksheet_file(title, audience, ws_num, ws_name, body)

        # Filename: basename-worksheet-N.md
        out_name = f"{basename}-worksheet-{ws_num}.md"
        out_path = os.path.join(audience_dir, out_name)

        with open(out_path, "w") as f:
            f.write(ws_content)

        stats["created"] += 1


def main():
    # Process all audience variant files
    files = sorted(glob.glob(os.path.join(SRC, "**", "*.md"), recursive=True))
    for fpath in files:
        process_file(fpath)

    print(f"Done.")
    print(f"  Standalone worksheets created: {stats['created']}")
    print(f"  Expected (1343 × 2): 2686")
    print(f"  Errors: {len(stats['errors'])}")
    print(f"  Generic Worksheet 1 prompts: {stats['generic_w1']}")
    print(f"  Generic Worksheet 2 prompts: {stats['generic_w2']}")

    if stats["errors"]:
        print(f"\nFirst 10 errors:")
        for e in stats["errors"][:10]:
            print(f"  {e}")


if __name__ == "__main__":
    main()
