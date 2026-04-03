#!/usr/bin/env python3
"""
Strip em dashes from all markdown content files.
Replaces:
  - " — " (space-em-space) with ": "
  - "—" (bare em dash) with ": "
  - HTML entity "&mdash;" with ": "
"""
import os
import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

def fix_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    # Replace space-padded em dash first, then bare em dash, then HTML entity
    new_text = re.sub(r'\s*—\s*', ': ', text)
    new_text = re.sub(r'&mdash;', ': ', new_text)
    if new_text == text:
        return 0
    path.write_text(new_text, encoding="utf-8")
    return 1

def main():
    if not CONTENT_DIR.is_dir():
        print(f"Content dir not found: {CONTENT_DIR}", file=sys.stderr)
        sys.exit(1)

    fixed = 0
    total = 0
    for md_file in sorted(CONTENT_DIR.rglob("*.md")):
        total += 1
        fixed += fix_file(md_file)

    print(f"Scanned: {total}  Fixed: {fixed}  Clean: {total - fixed}")

if __name__ == "__main__":
    main()
