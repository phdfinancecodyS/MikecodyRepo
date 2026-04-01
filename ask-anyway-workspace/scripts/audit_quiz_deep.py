#!/usr/bin/env python3
"""Deep audit of topic-matcher hint references against actual guide files."""
import json, os, glob

with open("quiz/base-guide-catalog.json") as f:
    catalog = json.load(f)

with open("quiz/topic-catalog.json") as f:
    topics = json.load(f)

with open("quiz/topic-matcher-flow.json") as f:
    matcher = json.load(f)

# Build lookup: guide_id -> guide data
guide_map = {g["guide_id"]: g for g in catalog["guides"]}

# Build lookup: chapter number -> guide(s) that source from it
source_map = {}
for g in catalog["guides"]:
    src = g.get("source", "")
    source_map.setdefault(src, []).append(g)

# Build lookup: topic catalog id -> topic
topic_map = {t["id"]: t for t in topics["topics"]}

# Check topic-matcher topicHints
print("=== Topic Matcher Hint Resolution ===")
all_hints = set()
for q in matcher["questions"]:
    for opt in q.get("options", []):
        for hint in opt.get("topicHints", []):
            all_hints.add(hint)

if not all_hints:
    print("  No topicHints found in matcher questions.")
else:
    for hint in sorted(all_hints):
        # Hints are like "ch02", "ch04", etc.
        # Check if topic catalog has this
        in_topic_catalog = hint in topic_map
        
        # Check if a guide exists - try multiple formats
        # ch02 -> ch-02 (guide_id)
        guide_id_fmt = hint[:2] + "-" + hint[2:]
        in_guide_catalog = guide_id_fmt in guide_map
        
        # Also check by source (e.g., source "Ch2" or "Ch02")
        ch_num = int(hint[2:])
        source_fmts = [f"Ch{ch_num}", f"Ch{ch_num:02d}"]
        has_source = any(sf in source_map for sf in source_fmts)
        
        # Check if actual file exists
        file_found = len(glob.glob(f"content/topic-guides/chapters/{guide_id_fmt}-*.md")) > 0
        
        status_parts = []
        if in_topic_catalog:
            status_parts.append("topic-catalog:YES")
        else:
            status_parts.append("topic-catalog:NO")
        if in_guide_catalog:
            status_parts.append("guide-catalog:YES")
        else:
            status_parts.append("guide-catalog:NO")
        if file_found:
            status_parts.append("file:YES")
        else:
            # Check splits that source from this chapter
            split_sources = source_map.get(f"Ch{ch_num:02d}", source_map.get(f"Ch{ch_num}", []))
            if split_sources:
                split_ids = [s["guide_id"] for s in split_sources]
                status_parts.append(f"file:NO (but splits exist: {split_ids})")
            else:
                status_parts.append("file:NO")
        
        ok = "OK" if (in_guide_catalog or has_source) and (file_found or has_source) else "BROKEN"
        title = topic_map.get(hint, {}).get("title", "???")
        print(f"  {hint} -> {title} [{ok}] ({', '.join(status_parts)})")

# Check topic-catalog entries map to either direct guides or split guides
print()
print("=== Topic Catalog -> Guide Resolution ===")
broken_topics = []
for t in topics["topics"]:
    tid = t["id"]
    ch_num = t.get("chapter")
    guide_id_fmt = tid[:2] + "-" + tid[2:]
    
    # Direct match
    if guide_id_fmt in guide_map:
        continue
    
    # Source match (splits/new)
    source_fmts = [f"Ch{ch_num}", f"Ch{ch_num:02d}"] if ch_num else []
    has_splits = any(sf in source_map for sf in source_fmts)
    if has_splits:
        continue
    
    # chapter_id match (splits that now have chapter_id set)
    chapter_id_match = any(g.get("chapter_id") == tid for g in catalog["guides"])
    if chapter_id_match:
        continue
    
    broken_topics.append((tid, t["title"]))

if broken_topics:
    for tid, title in broken_topics:
        print(f"  BROKEN: {tid} -> {title}")
else:
    print("  All topic catalog entries resolve to guides or splits.")

# Verify actual file count
print()
print("=== File Count Verification ===")
ch_files = glob.glob("content/topic-guides/chapters/ch-*.md")
split_files = glob.glob("content/topic-guides/splits/split-*.md")
new_files = glob.glob("content/topic-guides/new-topics/new-*.md")
audience_files = glob.glob("content/topic-guides/audience-slants/**/*.md", recursive=True)
print(f"  Chapter files: {len(ch_files)}")
print(f"  Split files: {len(split_files)}")
print(f"  New-topic files: {len(new_files)}")
print(f"  Audience variant files: {len(audience_files)}")
print(f"  Total: {len(ch_files) + len(split_files) + len(new_files) + len(audience_files)}")
