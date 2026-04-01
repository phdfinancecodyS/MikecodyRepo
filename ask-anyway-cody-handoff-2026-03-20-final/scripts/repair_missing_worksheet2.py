#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_FOLDERS = [
    ROOT / "content" / "topic-guides" / "chapters",
    ROOT / "content" / "topic-guides" / "splits",
    ROOT / "content" / "topic-guides" / "new-topics",
]

STANDARD_WORKSHEET2 = """Goal: Turn insight into one script and one 24-hour commitment.

Prompts:
- Script I will use word-for-word next time:
- My 90-second reset routine:
- One action I will take in the next 24 hours:
- The person I will check in with:
- How I will measure success by tomorrow night:"""


def replace_section(text, heading, body):
    pattern = re.compile(rf"(^## {re.escape(heading)}\n\n)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    return pattern.sub(lambda m: m.group(1) + body.strip() + "\n\n", text)


def main():
    fixed = 0
    for folder in BASE_FOLDERS:
        for path in sorted(folder.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            match = re.search(r"^## Worksheet 2: Action Builder\n\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
            body = match.group(1).strip() if match else ""
            if "Prompts:" not in body or not re.search(r"^\-\s+", body, re.MULTILINE):
                updated = replace_section(text, "Worksheet 2: Action Builder", STANDARD_WORKSHEET2)
                path.write_text(updated, encoding="utf-8")
                fixed += 1
                print(f"Fixed worksheet2: {path.name}")
    print(f"Worksheet 2 repairs complete: {fixed}")


if __name__ == "__main__":
    main()
