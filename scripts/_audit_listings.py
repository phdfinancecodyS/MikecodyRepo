#!/usr/bin/env python3
"""Pre-upload audit for all 79 Ask Anyway Etsy listings."""

import json, os, re, struct
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent

with open(ROOT / "output/etsy/listings.json") as f:
    data = json.load(f)
listings = data["listings"]

print(f"Total listings loaded: {len(listings)}")

critical = []
major = []
minor = []

REQUIRED_FIELDS = [
    "guide_id", "title", "description", "tags", "price",
    "pdf_path", "who_made", "when_made", "is_supply", "type", "quantity"
]


def png_dimensions(path):
    try:
        with open(path, "rb") as f:
            sig = f.read(8)
            if sig[:4] != b'\x89PNG':
                return None, None
            f.read(4)
            f.read(4)
            w = struct.unpack(">I", f.read(4))[0]
            h = struct.unpack(">I", f.read(4))[0]
            return w, h
    except Exception:
        return None, None


guide_ids_seen = []
pdf_exists_count = 0
pdf_missing = []
image_ok_count = 0
image_issues = []
title_ok = 0
tag_ok = 0
desc_ok = 0
em_dash_hits = []
placeholder_hits = []
intent_ok = 0
intent_issues = []
safety_ok = 0
safety_issues = []
policy_issues = []

EM_DASH_RE = re.compile(r'[\u2014\u2013]')
PLACEHOLDER_RE = re.compile(
    r'\b(lorem ipsum|TODO|TBD|FIXME|XXX|placeholder|REPLACE ME)\b', re.I
)
MEDICAL_PROMISE_RE = re.compile(
    r'\b(cure|treat|diagnose|heal|therapy session|clinical treatment|guaranteed|100%)\b', re.I
)

for idx, L in enumerate(listings):
    gid = L.get("guide_id", f"MISSING-{idx}")
    guide_ids_seen.append(gid)

    # 1. Required fields
    for field in REQUIRED_FIELDS:
        val = L.get(field)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            critical.append({
                "severity": "CRITICAL", "guide_id": gid, "field": field,
                "issue": "Missing or empty required field",
                "evidence": f"Value: {repr(val)}"
            })

    # 2. Title constraints
    title = L.get("title", "")
    if len(title) > 140:
        critical.append({
            "severity": "CRITICAL", "guide_id": gid, "field": "title",
            "issue": f"Title too long ({len(title)} chars, max 140)",
            "evidence": title[:80] + "..."
        })
    else:
        title_ok += 1

    # 3. Tags constraints
    tags = L.get("tags", [])
    if len(tags) != 13:
        major.append({
            "severity": "MAJOR", "guide_id": gid, "field": "tags",
            "issue": f"Tag count is {len(tags)}, expected 13",
            "evidence": str(tags[:5])
        })
    else:
        tag_ok += 1
    for t in tags:
        if len(t) > 20:
            critical.append({
                "severity": "CRITICAL", "guide_id": gid, "field": "tags",
                "issue": f"Tag too long ({len(t)} chars, max 20)",
                "evidence": t
            })
        if re.search(r'[<>{}|\\^~\[\]`]', t):
            major.append({
                "severity": "MAJOR", "guide_id": gid, "field": "tags",
                "issue": "Tag has illegal characters", "evidence": t
            })

    # 4. PDF exists
    pdf_path = ROOT / L.get("pdf_path", "")
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        pdf_exists_count += 1
    else:
        critical.append({
            "severity": "CRITICAL", "guide_id": gid, "field": "pdf_path",
            "issue": "PDF file missing or empty",
            "evidence": str(L.get("pdf_path", ""))
        })
        pdf_missing.append(gid)

    # 5. Images exist + dimensions
    img_dir = ROOT / "output" / "etsy" / "listing-images" / gid
    for img_num in [1, 2, 3, 4]:
        img_path = img_dir / f"image-{img_num}.png"
        if not img_path.exists():
            critical.append({
                "severity": "CRITICAL", "guide_id": gid,
                "field": f"image-{img_num}", "issue": "Image file missing",
                "evidence": str(img_path.relative_to(ROOT))
            })
        elif img_path.stat().st_size == 0:
            critical.append({
                "severity": "CRITICAL", "guide_id": gid,
                "field": f"image-{img_num}", "issue": "Image file is 0 bytes",
                "evidence": str(img_path.relative_to(ROOT))
            })
        else:
            w, h = png_dimensions(img_path)
            if w == 2000 and h == 2000:
                image_ok_count += 1
            elif w and h:
                major.append({
                    "severity": "MAJOR", "guide_id": gid,
                    "field": f"image-{img_num}",
                    "issue": f"Wrong dimensions: {w}x{h} (expected 2000x2000)",
                    "evidence": str(img_path.relative_to(ROOT))
                })
                image_issues.append((gid, img_num, w, h))
            else:
                major.append({
                    "severity": "MAJOR", "guide_id": gid,
                    "field": f"image-{img_num}",
                    "issue": "Could not read PNG dimensions",
                    "evidence": str(img_path.relative_to(ROOT))
                })

    # 6. Description quality
    desc = L.get("description", "")
    if len(desc) < 100:
        major.append({
            "severity": "MAJOR", "guide_id": gid, "field": "description",
            "issue": f"Description too short ({len(desc)} chars)",
            "evidence": desc[:80]
        })
    else:
        desc_ok += 1

    # 7. Em dash scan
    for field_name in ["title", "description"]:
        text = L.get(field_name, "")
        matches = EM_DASH_RE.findall(text)
        if matches:
            em_dash_hits.append({"guide_id": gid, "field": field_name, "count": len(matches)})
            major.append({
                "severity": "MAJOR", "guide_id": gid, "field": field_name,
                "issue": f"Contains {len(matches)} em/en dash(es)",
                "evidence": text[:80] if field_name == "title" else "In description body"
            })

    # 8. Placeholder scan
    for field_name in ["title", "description"]:
        text = L.get(field_name, "")
        pmatches = PLACEHOLDER_RE.findall(text)
        if pmatches:
            placeholder_hits.append({"guide_id": gid, "field": field_name, "matches": pmatches})
            critical.append({
                "severity": "CRITICAL", "guide_id": gid, "field": field_name,
                "issue": "Contains placeholder text", "evidence": str(pmatches)
            })

    # 9. Intent quality
    all_text = (title + " " + desc).lower()
    has_what_to_say = bool(re.search(r'what to say|exact words|scripts?', all_text))
    has_action_plan = bool(re.search(r'24.hour action plan|action plan|next step', all_text))
    has_worksheets = bool(re.search(r'worksheet', all_text))
    has_crisis = bool(re.search(r'988|crisis text line|741741', all_text))
    has_educational = bool(re.search(r'educational purposes|not therapy|not a clinical diagnosis', all_text))

    intent_score = sum([has_what_to_say, has_action_plan, has_worksheets, has_crisis, has_educational])
    if intent_score >= 4:
        intent_ok += 1
    else:
        missing = []
        if not has_what_to_say:
            missing.append("conversation scripts mention")
        if not has_action_plan:
            missing.append("action plan mention")
        if not has_worksheets:
            missing.append("worksheets mention")
        if not has_crisis:
            missing.append("crisis resources")
        if not has_educational:
            missing.append("educational disclaimer")
        intent_issues.append({"guide_id": gid, "score": intent_score, "missing": missing})
        sev = "CRITICAL" if not has_crisis or not has_educational else "MAJOR"
        bucket = critical if sev == "CRITICAL" else major
        bucket.append({
            "severity": sev, "guide_id": gid, "field": "description",
            "issue": f"Intent quality score {intent_score}/5, missing: {', '.join(missing)}",
            "evidence": ""
        })

    # 10. Safety / policy
    prom = MEDICAL_PROMISE_RE.findall(desc)
    if prom:
        real_issues = [p for p in prom if p.lower() not in ("guaranteed",)]
        if real_issues:
            policy_issues.append({"guide_id": gid, "matches": real_issues})
            minor.append({
                "severity": "MINOR", "guide_id": gid, "field": "description",
                "issue": f"Potential medical/therapeutic language: {real_issues}",
                "evidence": "Review manually"
            })

    if not has_crisis:
        safety_issues.append(gid)
    else:
        safety_ok += 1

# 11. Duplicate guide_ids
id_counts = Counter(guide_ids_seen)
for gid, cnt in id_counts.items():
    if cnt > 1:
        critical.append({
            "severity": "CRITICAL", "guide_id": gid, "field": "guide_id",
            "issue": f"Duplicate guide_id appears {cnt} times", "evidence": ""
        })

# 12. Price sanity
prices = [L.get("price", 0) for L in listings]
for L in listings:
    p = L.get("price", 0)
    if not isinstance(p, (int, float)) or p <= 0:
        critical.append({
            "severity": "CRITICAL", "guide_id": L.get("guide_id", "?"),
            "field": "price", "issue": f"Invalid price: {p}", "evidence": ""
        })

# ══════════════════════════════════════════════════════════
#  REPORT
# ══════════════════════════════════════════════════════════
print()
print("=" * 70)
print("    ASK ANYWAY ETSY LISTING AUDIT REPORT")
print("    Generated: 2026-03-25")
print("=" * 70)

print("\n-- A) EXECUTIVE SUMMARY --")
print(f"  Total listings audited:      {len(listings)}")
print(f"  Expected:                    79")
print(f"  Critical issues:             {len(critical)}")
print(f"  Major issues:                {len(major)}")
print(f"  Minor issues:                {len(minor)}")

blocked_ids = set(i["guide_id"] for i in critical)
major_only_ids = set(i["guide_id"] for i in major) - blocked_ids
clean_ids = set(guide_ids_seen) - blocked_ids - major_only_ids
print(f"  Listings with 0 issues:      {len(clean_ids)}")
print(f"  Listings blocked (critical): {len(blocked_ids)}")

verdict = "NOT READY" if len(critical) > 0 else "READY"
print(f"\n  >>> UPLOAD VERDICT: {verdict} <<<")

print(f"\n-- B) COVERAGE REPORT --")
print(f"  PDFs verified on disk:       {pdf_exists_count}/{len(listings)}")
print(f"  PDFs missing:                {len(pdf_missing)} {pdf_missing if pdf_missing else ''}")
print(f"  Images OK (2000x2000):       {image_ok_count}/{len(listings) * 4}")
print(f"  Images with dim issues:      {len(image_issues)}")
print(f"  Titles <= 140 chars:         {title_ok}/{len(listings)}")
print(f"  Tags == 13 per listing:      {tag_ok}/{len(listings)}")
print(f"  Descriptions adequate:       {desc_ok}/{len(listings)}")
print(f"  Intent quality >= 4/5:       {intent_ok}/{len(listings)}")
print(f"  Crisis resources present:    {safety_ok}/{len(listings)}")
print(f"  Em dash occurrences:         {len(em_dash_hits)} fields")
print(f"  Placeholder text found:      {len(placeholder_hits)} fields")
print(f"  Duplicate guide_ids:         {sum(1 for c in id_counts.values() if c > 1)}")
print(f"  Price range:                 ${min(prices):.2f} - ${max(prices):.2f}")
print(f"  Policy flags (review):       {len(policy_issues)}")

if critical:
    print(f"\n-- C) CRITICAL FINDINGS (blocks upload) --")
    for c in critical:
        print(f"  [{c['severity']}] {c['guide_id']} | {c['field']} | {c['issue']}")
        if c.get("evidence"):
            print(f"           Evidence: {c['evidence'][:120]}")

if major:
    print(f"\n-- D) MAJOR FINDINGS (should fix before upload) --")
    for m in major:
        print(f"  [{m['severity']}] {m['guide_id']} | {m['field']} | {m['issue']}")
        if m.get("evidence"):
            print(f"           Evidence: {m['evidence'][:120]}")

if minor:
    print(f"\n-- E) MINOR FINDINGS (polish, can ship with awareness) --")
    for m in minor[:50]:
        print(f"  [{m['severity']}] {m['guide_id']} | {m['field']} | {m['issue']}")

print(f"\n-- F) TOP 10 HIGHEST-RISK LISTINGS --")
risk_scores = {}
for item in critical + major:
    gid = item["guide_id"]
    w = 3 if item["severity"] == "CRITICAL" else 1
    risk_scores[gid] = risk_scores.get(gid, 0) + w
top10 = sorted(risk_scores.items(), key=lambda x: -x[1])[:10]
for rank, (gid, score) in enumerate(top10, 1):
    issues_for = [i for i in critical + major if i["guide_id"] == gid]
    summary = "; ".join(set(i["issue"][:60] for i in issues_for[:3]))
    print(f"  {rank}. {gid} (risk score {score}): {summary}")

print(f"\n-- G) TAG ANALYSIS --")
all_tags = []
for L in listings:
    all_tags.extend(L.get("tags", []))
tag_freq = Counter(all_tags)
print(f"  Unique tags used:            {len(tag_freq)}")
print(f"  Most common tags:")
for tag, cnt in tag_freq.most_common(15):
    print(f"    {cnt:3d}x  {tag}")

long_tags = [(t, len(t)) for t in tag_freq if len(t) > 20]
if long_tags:
    print(f"  Tags exceeding 20 chars:")
    for t, tl in long_tags:
        print(f"    '{t}' ({tl} chars)")
else:
    print(f"  All tags <= 20 chars: PASS")

# Duplicate tag detection per listing
dup_tag_listings = []
for L in listings:
    tags = L.get("tags", [])
    if len(tags) != len(set(tags)):
        dupes = [t for t, c in Counter(tags).items() if c > 1]
        dup_tag_listings.append((L["guide_id"], dupes))
if dup_tag_listings:
    print(f"  Listings with duplicate tags: {len(dup_tag_listings)}")
    for gid, dupes in dup_tag_listings:
        print(f"    {gid}: {dupes}")
        major.append({
            "severity": "MAJOR", "guide_id": gid, "field": "tags",
            "issue": f"Duplicate tags within listing: {dupes}", "evidence": ""
        })
else:
    print(f"  Duplicate tags within listings: NONE")

print(f"\n-- H) TITLE LENGTH DISTRIBUTION --")
lengths = [len(L.get("title", "")) for L in listings]
buckets = {"0-80": 0, "81-100": 0, "101-120": 0, "121-140": 0, "141+": 0}
for l in lengths:
    if l <= 80: buckets["0-80"] += 1
    elif l <= 100: buckets["81-100"] += 1
    elif l <= 120: buckets["101-120"] += 1
    elif l <= 140: buckets["121-140"] += 1
    else: buckets["141+"] += 1
for k, v in buckets.items():
    bar = "#" * v
    print(f"  {k:>7s}: {v:2d} {bar}")

print(f"\n-- I) FINAL GATE --")
total_crit = len(critical)
total_maj = len(major)
if total_crit == 0 and total_maj == 0:
    print("  SAFE TO UPLOAD NOW.")
    print("  All 79 listings pass all checks.")
elif total_crit == 0:
    print(f"  CONDITIONAL PASS: 0 critical, {total_maj} major issues.")
    print("  Recommend fixing major issues but upload is technically possible.")
else:
    print(f"  DO NOT UPLOAD YET.")
    print(f"  {total_crit} critical blocker(s) must be resolved first.")
    print(f"  Minimum fix set:")
    seen = set()
    for c in critical:
        key = (c["guide_id"], c["field"], c["issue"][:40])
        if key not in seen:
            seen.add(key)
            print(f"    - {c['guide_id']}: {c['issue'][:80]}")

print()
print("=" * 70)
print("    END OF AUDIT REPORT")
print("=" * 70)
