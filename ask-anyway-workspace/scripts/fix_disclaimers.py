#!/usr/bin/env python3
"""Scan all content files for missing disclaimer, then add it where missing."""
import glob, os

DISCLAIMER = """

---

> **Disclaimer:** This content is for educational purposes only and is not a substitute for professional mental health treatment. If you or someone you know is in crisis, contact the **988 Suicide & Crisis Lifeline** by calling or texting **988**, or text **HOME** to **741741** to reach the Crisis Text Line.
"""

disclaimer_marker = "educational purposes"

all_files = (
    glob.glob("content/topic-guides/chapters/ch-*.md") +
    glob.glob("content/topic-guides/splits/split-*.md") +
    glob.glob("content/topic-guides/new-topics/new-*.md") +
    glob.glob("content/topic-guides/audience-slants/**/*.md", recursive=True) +
    glob.glob("content/worksheets/**/*.md", recursive=True) +
    glob.glob("content/modules/module-*.md") +
    glob.glob("content/lead-magnet/*.md")
)

missing = []
for f in all_files:
    with open(f) as fh:
        content = fh.read()
    if disclaimer_marker.lower() not in content.lower():
        missing.append(f)

print(f"Total files scanned: {len(all_files)}")
print(f"Missing disclaimer: {len(missing)}")

if not missing:
    print("Nothing to fix.")
    exit(0)

# Categorize for reporting
cats = {}
for m in missing:
    rel = os.path.relpath(m)
    if "/audience-slants/" in m:
        cats.setdefault("audience-slants", []).append(rel)
    elif "/worksheets/" in m:
        cats.setdefault("worksheets", []).append(rel)
    elif "/chapters/" in m:
        cats.setdefault("chapters", []).append(rel)
    elif "/splits/" in m:
        cats.setdefault("splits", []).append(rel)
    elif "/new-topics/" in m:
        cats.setdefault("new-topics", []).append(rel)
    else:
        cats.setdefault("other", []).append(rel)

for cat, files in cats.items():
    print(f"  {cat}: {len(files)}")
    for f in files[:3]:
        print(f"    {f}")
    if len(files) > 3:
        print(f"    ...and {len(files)-3} more")

# Fix: append disclaimer to each missing file
fixed = 0
errors = 0
for f in missing:
    try:
        with open(f) as fh:
            content = fh.read()
        # Strip trailing whitespace/newlines, then append disclaimer
        content = content.rstrip() + DISCLAIMER
        with open(f, "w") as fh:
            fh.write(content)
        fixed += 1
    except Exception as e:
        print(f"  ERROR fixing {f}: {e}")
        errors += 1

print(f"\nFixed: {fixed}")
print(f"Errors: {errors}")
