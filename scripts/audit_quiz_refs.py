#!/usr/bin/env python3
"""Audit quiz catalog references and find broken links."""
import json

# Load catalogs
with open("quiz/base-guide-catalog.json") as f:
    catalog = json.load(f)

with open("quiz/topic-catalog.json") as f:
    topics = json.load(f)

with open("quiz/topic-matcher-flow.json") as f:
    matcher = json.load(f)

# Get all guide_ids from base catalog
guide_ids = set(g["guide_id"] for g in catalog["guides"])
print(f"Base guide catalog: {len(guide_ids)} guides")
print(f"  Chapters: {sorted(i for i in guide_ids if i.startswith('ch-'))}")
print(f"  Splits: {len([i for i in guide_ids if i.startswith('split-')])}")
print(f"  New: {len([i for i in guide_ids if i.startswith('new-')])}")
print()

# Check topic catalog references
print("=== Topic Catalog Reference Check ===")
topic_ids_in_catalog = set()
missing_from_guides = []
for t in topics["topics"]:
    tid = t["id"]
    topic_ids_in_catalog.add(tid)
    # Topic IDs use format "ch01" but guide_ids use "ch-01"
    # Convert: ch01 -> ch-01, ch10 -> ch-10
    normalized = tid[:2] + "-" + tid[2:]
    if normalized not in guide_ids:
        # Maybe it maps to a split
        matching_guides = [g for g in catalog["guides"] if g.get("source", "").lower() == tid.lower()]
        if not matching_guides:
            missing_from_guides.append((tid, t["title"]))
            print(f"  MISSING: {tid} -> {t['title']}")

if not missing_from_guides:
    print("  All topic catalog entries have matching guides.")
print()

# Check topic-matcher-flow hints
print("=== Topic Matcher Flow Hint Check ===")
all_hint_ids = set()
for q in matcher.get("questions", []):
    for opt in q.get("options", []):
        hints = opt.get("topic_hints", [])
        for h in hints:
            all_hint_ids.add(h)

missing_hints = []
for hint in sorted(all_hint_ids):
    normalized = hint[:2] + "-" + hint[2:] if not "-" in hint else hint
    if normalized not in guide_ids:
        missing_hints.append(hint)
        print(f"  MISSING hint target: {hint}")

if not missing_hints:
    print("  All topic matcher hints reference valid guides.")
print()

# Summary
print("=== SUMMARY ===")
print(f"Topic catalog entries: {len(topics['topics'])}")
print(f"Base guide catalog entries: {len(guide_ids)}")
print(f"Topic matcher hint IDs: {len(all_hint_ids)}")
print(f"Missing from guides: {len(missing_from_guides)}")
print(f"Missing hint targets: {len(missing_hints)}")
