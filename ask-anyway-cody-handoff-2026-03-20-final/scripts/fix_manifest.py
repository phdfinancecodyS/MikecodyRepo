#!/usr/bin/env python3
"""Add missing chapter entries to GUIDE-BUILD-MANIFEST.csv."""
import glob

with open("planning/GUIDE-BUILD-MANIFEST.csv") as f:
    lines = f.readlines()

header = lines[0]
existing = lines[1:]

chapter_rows = []
for fp in sorted(glob.glob("content/topic-guides/chapters/ch-*.md")):
    d = {}
    with open(fp) as fh:
        for line in fh:
            if line.startswith("# "):
                d["title"] = line[2:].strip()
            elif line.startswith("Guide ID:"):
                d["id"] = line.split(":", 1)[1].strip()
            elif line.startswith("Source:"):
                d["source"] = line.split(":", 1)[1].strip()
            elif line.startswith("Status:"):
                d["status"] = line.split(":", 1)[1].strip()
            elif line.startswith("Batch:"):
                d["batch"] = line.split(":", 1)[1].strip()
            elif line.startswith("Priority:"):
                d["priority"] = line.split(":", 1)[1].strip()
            elif line.startswith("## "):
                break
    title = d["title"]
    if "," in title:
        title = '"' + title + '"'
    row = ",".join([d["id"], "chapter", title, d["source"], d["status"], d["batch"], d["priority"]])
    chapter_rows.append(row + "\n")

with open("planning/GUIDE-BUILD-MANIFEST.csv", "w") as f:
    f.write(header)
    for row in chapter_rows:
        f.write(row)
    for row in existing:
        f.write(row)

print(f"Done. {len(chapter_rows)} chapter rows added + {len(existing)} existing = {len(chapter_rows) + len(existing)} total entries.")
