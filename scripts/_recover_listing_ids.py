#!/usr/bin/env python3
"""Recover listing IDs from first upload attempt and save to progress file."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The listing IDs from the first upload in order (extracted from terminal output)
LISTING_IDS = [
    4477712159, 4477718612, 4477712209, 4477718652, 4477712239,
    4477712245, 4477712265, 4477718740, 4477712297, 4477712315,
    4477712333, 4477718808, 4477718820, 4477718834, 4477718856,
    4477718872, 4477718894, 4477712475, 4477718936, 4477712517,
    4477712541, 4477719002, 4477712589, 4477712617, 4477719078,
    4477719090, 4477719112, 4477719134, 4477719154, 4477712707,
    4477712735, 4477712761, 4477719230, 4477712801, 4477712829,
    4477719268, 4477719296, 4477712887, 4477719340, 4477712931,
    4477719392, 4477712981, 4477719424, 4477719448, 4477719466,
    4477713065, 4477713079, 4477713103, 4477713131, 4477719552,
    4477719572, 4477713183, 4477713203, 4477713227, 4477719662,
    4477719692, 4477719714, 4477713323, 4477719744, 4477719762,
    4477719786, 4477713371, 4477719852, 4477719858, 4477719886,
    4477719912, 4477719934, 4477713487, 4477713503, 4477720004,
    4477713539, 4477720048, 4477713589, 4477720102, 4477713613,
    4477720136, 4477713647, 4477720168, 4477713687,
]

with open(ROOT / "output/etsy/listings.json") as f:
    listings = json.load(f)["listings"]

assert len(LISTING_IDS) == len(listings) == 79, f"Mismatch: {len(LISTING_IDS)} IDs, {len(listings)} listings"

progress = {"completed": {}, "errors": []}
for i, listing in enumerate(listings):
    gid = listing["guide_id"]
    progress["completed"][gid] = {
        "listing_id": LISTING_IDS[i],
        "title": listing["title"],
        "needs_files": True,
    }

out = ROOT / "output/etsy/upload_progress.json"
with open(out, "w") as f:
    json.dump(progress, f, indent=2)

print(f"Saved {len(progress['completed'])} listing ID mappings")
print(f"First: {listings[0]['guide_id']} -> {LISTING_IDS[0]}")
print(f"Last:  {listings[-1]['guide_id']} -> {LISTING_IDS[-1]}")
