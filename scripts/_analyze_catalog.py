#!/usr/bin/env python3
"""Analyze guide catalog metadata for Etsy listing generation."""
import json

data = json.load(open("quiz/base-guide-catalog.json"))
guides = data["guides"]
print(f"Total guides: {len(guides)}")
print()

all_tags = set()
all_domains = set()
all_clusters = set()
for g in guides:
    all_tags.update(g.get("tags", []))
    all_domains.add(g.get("domain", ""))
    all_clusters.add(g.get("cluster", ""))

print(f"Unique tags ({len(all_tags)}): {sorted(all_tags)}")
print()
print(f"Domains ({len(all_domains)}): {sorted(all_domains)}")
print()
print(f"Clusters ({len(all_clusters)}): {sorted(all_clusters)}")
print()

for g in guides:
    print(f"{g['guide_id']}: {g['title']} | tags={g.get('tags',[])} domain={g.get('domain','')} cluster={g.get('cluster','')}")
