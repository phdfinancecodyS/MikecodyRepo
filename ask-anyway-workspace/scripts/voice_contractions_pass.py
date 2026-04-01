#!/usr/bin/env python3
"""
Voice pass 1: Add natural contractions to all guide files.
Skips metadata lines (Status:, Guide ID:, etc.) and section headers (## lines).
Applies to body text only.
"""
import os, re, glob

ROOTS = [
    "content/topic-guides/audience-slants",
    "content/topic-guides/chapters",
    "content/topic-guides/splits",
    "content/topic-guides/new-topics",
]

# Ordered replacements — longer phrases first to avoid partial matches.
# Each tuple: (pattern, replacement, is_regex)
REPLACEMENTS = [
    # Multi-word negatives (longer first)
    ("could not have", "couldn't have", False),
    ("should not have", "shouldn't have", False),
    ("would not have", "wouldn't have", False),
    ("does not have", "doesn't have", False),
    ("do not have", "don't have", False),
    ("did not have", "didn't have", False),
    ("will not", "won't", False),
    ("would not", "wouldn't", False),
    ("should not", "shouldn't", False),
    ("could not", "couldn't", False),
    ("does not", "doesn't", False),
    ("did not", "didn't", False),
    ("do not", "don't", False),
    ("cannot", "can't", False),
    ("can not", "can't", False),
    ("is not", "isn't", False),
    ("are not", "aren't", False),
    ("was not", "wasn't", False),
    ("were not", "weren't", False),
    ("have not", "haven't", False),
    ("has not", "hasn't", False),
    ("had not", "hadn't", False),
    # Pronoun contractions
    ("I am ", "I'm ", False),
    ("you are ", "you're ", False),
    ("we are ", "we're ", False),
    ("they are ", "they're ", False),
    ("it is ", "it's ", False),
    ("that is ", "that's ", False),
    ("there is ", "there's ", False),
    ("here is ", "here's ", False),
    ("what is ", "what's ", False),
    # Future tense
    ("I will ", "I'll ", False),
    ("you will ", "you'll ", False),
    ("we will ", "we'll ", False),
    ("they will ", "they'll ", False),
    # Perfect tense
    ("I have ", "I've ", False),
    ("you have ", "you've ", False),
    ("we have ", "we've ", False),
    ("they have ", "they've ", False),
    # Let us
    ("let us ", "let's ", False),
]

# Lines to skip: metadata, headers, status lines
SKIP_PREFIXES = (
    "#", "Status:", "Guide ID:", "Guide type:", "Source:", "Batch:",
    "Priority:", "Audience Bucket:", "Audience Tier:", "Base Guide Path:",
    "Goal:", "---",
)

def apply_contractions(text):
    lines = text.split("\n")
    new_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip metadata, headers, and horizontal rules
        if any(stripped.startswith(p) for p in SKIP_PREFIXES):
            new_lines.append(line)
            continue
        # Skip empty lines
        if not stripped:
            new_lines.append(line)
            continue
        # Apply replacements (case-insensitive with case preservation)
        for old, new, _ in REPLACEMENTS:
            # Match case-insensitively but preserve original case pattern
            idx = 0
            while True:
                lower_line = line.lower()
                pos = lower_line.find(old.lower(), idx)
                if pos == -1:
                    break
                # Check if the original starts with uppercase
                orig = line[pos:pos+len(old)]
                if orig[0].isupper():
                    replacement = new[0].upper() + new[1:]
                else:
                    replacement = new
                line = line[:pos] + replacement + line[pos+len(old):]
                idx = pos + len(replacement)
        new_lines.append(line)
    return "\n".join(new_lines)

def main():
    files_changed = 0
    total_files = 0
    for root in ROOTS:
        for fpath in glob.glob(os.path.join(root, "**", "*.md"), recursive=True):
            total_files += 1
            with open(fpath, "r") as f:
                original = f.read()
            updated = apply_contractions(original)
            if updated != original:
                with open(fpath, "w") as f:
                    f.write(updated)
                files_changed += 1
    print(f"Done. {files_changed}/{total_files} files updated with contractions.")

if __name__ == "__main__":
    main()
