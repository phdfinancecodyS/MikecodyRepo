#!/usr/bin/env python3
"""Build and apply a practical Etsy SEO optimization pass for live listings.

What this script does:
1. Loads current listing payloads from output/etsy/listings.json.
2. Builds stronger keyword-led titles and opening description lines.
3. Writes a preview plan to output/etsy/seo_push_plan.json.
4. Optionally PATCHes live Etsy listings using IDs from upload_progress.json.

Usage:
  python3 scripts/etsy_seo_push.py
  python3 scripts/etsy_seo_push.py --apply
  python3 scripts/etsy_seo_push.py --apply --limit 12
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import etsy_upload as etsy


ROOT = Path(__file__).resolve().parent.parent
LISTINGS_FILE = ROOT / "output" / "etsy" / "listings.json"
PROGRESS_FILE = ROOT / "output" / "etsy" / "upload_progress.json"
PLAN_FILE = ROOT / "output" / "etsy" / "seo_push_plan.json"

# Keep under Etsy tag max length (20 chars) and avoid broad low-intent terms.
WEAK_TAGS = {
    "mental health",
    "self help guide",
    "digital download",
    "coping skills",
    "printable worksheet",
    "conversation guide",
    "instant download",
    "mood support",
    "self improvement",
    "emotional control",
}

UNIVERSAL_TARGET_TAGS = [
    "printable worksheet",
    "conversation guide",
    "instant download",
]

TITLE_SUFFIX = " | Printable Worksheet PDF"


def _base_title(raw_title: str) -> str:
    """Remove old boilerplate title endings from generated listings."""
    patterns = [
        r"\s*-\s*Conversation Scripts\s*\+\s*Action Plan\s*-\s*Digital PDF\s*$",
        r"\s*-\s*Mental Health Guide\s*\+\s*Worksheets\s*-\s*Digital Download PDF\s*$",
        r"\s*-\s*Mental Health Guide and Worksheets\s*-\s*Digital Download PDF\s*$",
        r"\s*-\s*Mental Health Guide\s*\+\s*Worksheets\s*-\s*PDF\s*$",
        r"\s*-\s*Mental Health Guide and Worksheets\s*-\s*PDF\s*$",
    ]
    title = raw_title.strip()
    for pat in patterns:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", title).strip(" -|")


def _specific_tags(tags: list[str]) -> list[str]:
    """Get tags likely to carry buyer intent."""
    out: list[str] = []
    for t in tags:
        clean = t.strip().lower()
        if not clean or clean in WEAK_TAGS:
            continue
        if clean not in out:
            out.append(clean)
    return out


def _build_title(old_title: str, tags: list[str]) -> str:
    """Build a keyword-led title while staying within Etsy 140-char limit."""
    base = _base_title(old_title)
    intent = _specific_tags(tags)
    primary = intent[0].title() if intent else "Mental Health"

    if primary.lower() in base.lower():
        candidate = f"{base}{TITLE_SUFFIX}"
    else:
        candidate = f"{primary}: {base}{TITLE_SUFFIX}"

    candidate = _enforce_single_colon(candidate)

    if len(candidate) <= 140:
        return candidate

    # Shorten in stages before a hard cut.
    shorter = candidate.replace("Printable Worksheet PDF", "Printable PDF")
    shorter = _enforce_single_colon(shorter)
    if len(shorter) <= 140:
        return shorter

    shorter = shorter.replace("Conversation Scripts", "Scripts")
    shorter = _enforce_single_colon(shorter)
    if len(shorter) <= 140:
        return shorter

    return _enforce_single_colon(shorter[:140].rstrip(" ,:;|-."))


def _enforce_single_colon(title: str) -> str:
    """Etsy allows one colon in a title. Convert extras to hyphen separators."""
    if title.count(":") <= 1:
        return title

    out = []
    seen_colon = 0
    for ch in title:
        if ch == ":":
            seen_colon += 1
            if seen_colon == 1:
                out.append(ch)
            else:
                out.append(" -")
        else:
            out.append(ch)
    cleaned = "".join(out)
    cleaned = re.sub(r"\s+", " ", cleaned).replace("- -", "-")
    return cleaned.strip()


def _description_hook(tags: list[str], base_title: str) -> str:
    """Create a strong first line for description search relevance."""
    intent = _specific_tags(tags)
    primary = intent[0] if intent else "mental health support"
    secondary = intent[1] if len(intent) > 1 else "coping skills"
    return (
        f"{primary.title()} printable worksheet and conversation guide for {secondary}. "
        f"Instant download you can use today."
    )


def _replace_first_paragraph(description: str, new_first_paragraph: str) -> str:
    """Swap only the opening paragraph to avoid disturbing compliance sections."""
    parts = description.split("\n\n", 1)
    if len(parts) == 1:
        return new_first_paragraph
    return f"{new_first_paragraph}\n\n{parts[1]}"


def _build_tags(old_tags: list[str], title: str) -> list[str]:
    """Tighten tag quality while preserving topic-specific tags already present."""
    kept = [t.strip().lower() for t in old_tags if t.strip() and t.strip().lower() not in WEAK_TAGS]

    merged: list[str] = []
    for t in UNIVERSAL_TARGET_TAGS + kept:
        if t not in merged:
            merged.append(t)

    # Add a short keyword from title if there is room.
    low_title = title.lower()
    title_candidates = [
        "anxiety help",
        "burnout",
        "ptsd help",
        "grief support",
        "sleep help",
        "couples help",
        "relationship help",
        "suicide prevention",
    ]
    for tc in title_candidates:
        if tc in low_title and tc not in merged:
            merged.append(tc)

    fallback_tags = [
        "anxiety help",
        "stress relief",
        "emotional support",
        "self regulation",
        "trauma recovery",
        "burnout recovery",
        "mental wellness",
        "mindset reset",
        "printable pdf",
        "daily check in",
    ]

    for fb in fallback_tags:
        if len(merged) >= 13:
            break
        if fb not in merged:
            merged.append(fb)

    # Etsy max is 13 tags, but keep target full when possible.
    return merged[:13]


def build_plan(listings: list[dict], completed_map: dict) -> list[dict]:
    """Generate before/after SEO plan entries for live listings only."""
    plan: list[dict] = []
    for listing in listings:
        gid = listing["guide_id"]
        if gid not in completed_map:
            continue

        old_title = listing["title"]
        old_desc = listing["description"]
        old_tags = listing.get("tags", [])

        new_title = _build_title(old_title, old_tags)
        new_tags = _build_tags(old_tags, new_title)
        hook = _description_hook(new_tags, _base_title(old_title))
        new_desc = _replace_first_paragraph(old_desc, hook)

        plan.append(
            {
                "guide_id": gid,
                "listing_id": completed_map[gid]["listing_id"],
                "old_title": old_title,
                "new_title": new_title,
                "old_tags": old_tags,
                "new_tags": new_tags,
                "old_description_opening": old_desc.split("\n\n", 1)[0],
                "new_description_opening": hook,
                "new_description": new_desc,
            }
        )
    return plan


def apply_updates(plan: list[dict], api_key: str, access_token: str, shared_secret: str,
                  shop_id: int, limit: int = 0):
    """PATCH listing metadata updates to Etsy."""
    total = len(plan) if limit <= 0 else min(limit, len(plan))
    print(f"Applying updates to {total} listing(s)...")

    updated = 0
    failures = 0

    for entry in plan[:total]:
        listing_id = entry["listing_id"]
        payload = {
            "title": entry["new_title"],
            "description": entry["new_description"],
            "tags": entry["new_tags"],
        }
        try:
            etsy.api_request(
                "PATCH",
                f"/application/shops/{shop_id}/listings/{listing_id}",
                api_key,
                access_token,
                data=payload,
                shared_secret=shared_secret,
            )
            updated += 1
            print(f"  Updated {entry['guide_id']} ({listing_id})")
            time.sleep(etsy.RATE_LIMIT_DELAY)
        except Exception as exc:
            failures += 1
            print(f"  ERROR {entry['guide_id']} ({listing_id}): {exc}")
            time.sleep(0.5)

    print("\nSEO push complete")
    print(f"  Updated: {updated}")
    print(f"  Failed: {failures}")


def main():
    parser = argparse.ArgumentParser(description="Build/apply Etsy SEO optimization updates")
    parser.add_argument("--apply", action="store_true", help="Apply updates to Etsy via API")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of live updates")
    args = parser.parse_args()

    if not LISTINGS_FILE.exists() or not PROGRESS_FILE.exists():
        raise SystemExit("Missing listings.json or upload_progress.json")

    data = json.loads(LISTINGS_FILE.read_text(encoding="utf-8"))
    listings = data["listings"] if isinstance(data, dict) else data
    progress = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    completed_map = progress.get("completed", {})

    plan = build_plan(listings, completed_map)
    PLAN_FILE.write_text(json.dumps({"count": len(plan), "updates": plan}, indent=2), encoding="utf-8")

    print(f"Planned updates: {len(plan)}")
    print(f"Wrote: {PLAN_FILE}")
    if plan:
        print("Sample:")
        for sample in plan[:3]:
            print(f"  {sample['guide_id']}: {sample['new_title']}")

    if not args.apply:
        print("\nDry run only. Re-run with --apply to push updates.")
        return

    etsy.load_env()
    api_key = etsy.get_api_key()
    shared_secret = etsy.get_shared_secret()
    token = etsy.load_or_auth(api_key, force_auth=False)
    access_token = token["access_token"]

    shop_id_str = etsy.os.environ.get("ETSY_SHOP_ID", "")
    if shop_id_str:
        shop_id = int(shop_id_str)
    else:
        shop_id = etsy.get_shop_id(api_key, access_token, shared_secret)

    apply_updates(plan, api_key, access_token, shared_secret, shop_id, limit=args.limit)


if __name__ == "__main__":
    main()
