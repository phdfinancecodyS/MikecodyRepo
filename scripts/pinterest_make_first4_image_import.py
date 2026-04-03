#!/usr/bin/env python3
"""Generate a Pinterest image-import CSV for the first 4 scheduled pins.

This resolves two common import blockers:
1. Media URL must be a public HTTPS URL, not a local file path.
2. Video-only columns are omitted for image pin imports.
"""

import csv
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import etsy_upload as etsy


ROOT = Path(__file__).resolve().parent.parent
SCHEDULE = ROOT / "output" / "pinterest" / "pins_14day_schedule.csv"
OUT = ROOT / "output" / "pinterest" / "pins_first4_pinterest_image_import.csv"


def listing_id_from_url(url: str) -> int:
    match = re.search(r"/listing/(\d+)", url)
    if not match:
        raise ValueError(f"Could not parse listing ID from URL: {url}")
    return int(match.group(1))


def get_primary_image_url(listing_id: int, api_key: str, token: str, shared_secret: str) -> str:
    payload = etsy.api_request(
        "GET",
        f"/application/listings/{listing_id}/images",
        api_key,
        token,
        shared_secret=shared_secret,
    )
    results = payload.get("results", []) if isinstance(payload, dict) else []
    if not results:
        return ""

    first = sorted(results, key=lambda x: x.get("rank", 9999))[0]
    return first.get("url_fullxfull") or first.get("url_570xN") or first.get("url_170x135") or ""


def main():
    etsy.load_env()
    api_key = etsy.get_api_key()
    shared_secret = etsy.get_shared_secret()
    token = etsy.load_or_auth(api_key, force_auth=False)["access_token"]

    rows = []
    with SCHEDULE.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if len(rows) >= 4:
                break

            listing_id = listing_id_from_url(row["destination_url"])
            media_url = get_primary_image_url(listing_id, api_key, token, shared_secret)

            rows.append(
                {
                    "Title": row["pin_title"],
                    "Media URL": media_url,
                    "Pinterest board": row["board"],
                    "Description": "",
                    "Link": row["destination_url"],
                    "Publish date": row["publish_date"],
                }
            )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Title", "Media URL", "Pinterest board", "Description", "Link", "Publish date"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(OUT)


if __name__ == "__main__":
    main()
