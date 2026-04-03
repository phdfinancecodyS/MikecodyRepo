"""
Full tag overhaul for all 79 Etsy listings.

Changes:
  1. Swap `pdf guide`  -> `printable worksheet`  (buyers search "printable", not "pdf guide")
  2. Swap `wellness`   -> `conversation guide`   (brand differentiator; low competition)
  3. Fill remaining empty slots to reach 13 tags per listing
     using high-intent, topic-specific terms.

All tags verified <= 20 characters (Etsy limit).
"""

import json
from copy import deepcopy

# ── fill tags per listing index (1-based) ───────────────────────────────────
# Only tags NOT already present after the swap.
FILLS = {
    # 12-tag listings → need 1 fill
    1:  ["trauma recovery"],
    2:  ["ptsd help"],
    3:  ["anger management"],
    4:  ["depression help"],
    5:  ["self compassion"],
    6:  ["brain fog"],
    7:  ["burnout"],
    8:  ["anger management"],
    9:  ["sleep tips"],
    10: ["sleep improvement"],
    11: ["sensory overload"],
    12: ["sensory issues"],
    14: ["couples help"],
    15: ["couples help"],
    16: ["parenting stress"],
    17: ["parenting stress"],
    18: ["life transition"],
    19: ["relationship help"],
    21: ["relationship help"],
    23: ["relationship help"],
    25: ["relationship help"],
    27: ["emotional healing"],
    28: ["emotional healing"],
    29: ["grief support"],
    30: ["identity crisis"],
    31: ["burnout"],
    32: ["social isolation"],
    33: ["first responder"],
    34: ["anger management"],
    35: ["emotional shutdown"],
    36: ["ptsd help"],
    37: ["sleep anxiety"],
    38: ["suicide prevention"],
    39: ["suicide prevention"],
    40: ["adhd help"],
    41: ["adhd help"],
    42: ["ptsd nightmares"],
    43: ["sleep disorder"],
    44: ["chronic pain"],
    45: ["muscle tension"],
    46: ["brain injury"],
    47: ["chronic headache"],
    48: ["addiction recovery"],
    49: ["addiction recovery"],
    50: ["caregiver support"],
    51: ["caregiver support"],
    52: ["addiction recovery"],
    53: ["addiction recovery"],
    58: ["financial stress"],
    59: ["home organization"],
    60: ["screen addiction"],
    61: ["ocd help"],
    # 11-tag listings → need 2 fills
    13: ["anxiety help", "emotional safety"],
    20: ["relationship help", "low libido"],
    22: ["relationship help", "trauma recovery"],
    24: ["relationship help", "self esteem"],
    26: ["emotional healing", "first responder"],
    56: ["identity crisis", "retirement"],
    57: ["burnout", "anxiety help"],
    # 10-tag listings → need 3 fills
    54: ["couples help", "relationship repair", "shame recovery"],
    55: ["relationship repair", "trust issues", "couples help"],
    # 9-tag listings → need 4 fills
    62: ["panic attack", "anxiety attack", "anxiety help", "stress relief"],
    63: ["first responder", "trauma recovery", "burnout", "anxiety help"],
    64: ["grief support", "grief and loss", "loss support", "bereavement"],
    65: ["survivor guilt", "first responder", "trauma recovery", "emotional healing"],
    66: ["first responder", "work anxiety", "anxiety help", "emotional support"],
    67: ["shift work", "first responder", "couples help", "work life balance"],
    68: ["co parenting", "parenting stress", "family conflict", "burnout"],
    69: ["work anxiety", "anxiety help", "burnout recovery", "life transition"],
    70: ["peer support", "first responder", "workplace help", "conversation help"],
    71: ["asking for help", "emotional support", "anxiety help", "vulnerability"],
    72: ["safety planning", "suicide prevention", "crisis planning", "mental health plan"],
    73: ["helping someone", "mental health help", "suicide prevention", "caregiver support"],
    74: ["screen time", "dopamine detox", "social media detox", "anxiety help"],
    75: ["shift work", "sleep hygiene", "sleep tips", "anxiety help"],
    76: ["stress eating", "emotional eating", "anxiety help", "body awareness"],
    77: ["family boundaries", "setting boundaries", "first responder", "family conflict"],
    78: ["trauma recovery", "relationship anxiety", "hypervigilance", "couples help"],
    79: ["military veteran", "life transition", "career change", "first responder"],
}

REMOVE = {"pdf guide", "wellness"}
ADD    = ["printable worksheet", "conversation guide"]

data = json.load(open("output/etsy/listings.json", encoding="utf-8"))
listings = data if isinstance(data, list) else data.get("listings", data)

errors = []
for i, listing in enumerate(listings, 1):
    tags = listing.get("tags", [])

    # 1. Remove weak universal tags
    tags = [t for t in tags if t not in REMOVE]

    # 2. Add the two replacement universals (de-duped)
    for t in ADD:
        if t not in tags:
            tags.append(t)

    # 3. Fill to 13 with topic-specific tags (de-duped)
    for t in FILLS.get(i, []):
        if t not in tags:
            tags.append(t)

    # Validate
    for t in tags:
        if len(t) > 20:
            errors.append(f"#{i:02d} tag too long ({len(t)}): '{t}'")

    if len(tags) != 13:
        errors.append(f"#{i:02d} has {len(tags)} tags (expected 13) — topic: {listing['title'].split(' - ')[0]}")

    listing["tags"] = tags

if errors:
    print("ERRORS:")
    for e in errors:
        print(" ", e)
else:
    with open("output/etsy/listings.json", "w", encoding="utf-8") as f:
        json.dump(listings if isinstance(data, list) else data, f, ensure_ascii=False, indent=2)
    print(f"Done. All 79 listings updated to 13 tags.")
    print(f"\nSample check:")
    for idx in [1, 13, 26, 54, 62, 72, 79]:
        l = listings[idx - 1]
        topic = l["title"].split(" - ")[0][:50]
        print(f"  {idx:02d} ({len(l['tags'])} tags): {topic}")
        print(f"      {l['tags']}")
