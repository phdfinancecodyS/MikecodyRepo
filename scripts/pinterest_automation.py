#!/usr/bin/env python3
"""Generate Pinterest-ready assets from live Etsy listings.

Outputs:
  - output/pinterest/pins_master.csv
  - output/pinterest/pins_14day_schedule.csv
  - output/pinterest/pinterest_summary.json

Usage:
  python3 scripts/pinterest_automation.py
  python3 scripts/pinterest_automation.py --start-date 2026-03-27
  python3 scripts/pinterest_automation.py --daily-pins 5
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parent.parent
SEO_PLAN_FILE = ROOT / "output" / "etsy" / "seo_push_plan.json"
OUT_DIR = ROOT / "output" / "pinterest"
MASTER_CSV = OUT_DIR / "pins_master.csv"
SCHEDULE_CSV = OUT_DIR / "pins_14day_schedule.csv"
SUMMARY_JSON = OUT_DIR / "pinterest_summary.json"


def board_for_tags(tags: list[str]) -> str:
    low = {t.lower() for t in tags}
    if "suicide prevention" in low or "crisis planning" in low:
        return "Crisis Conversation Support"
    if "couples help" in low or "relationship help" in low:
        return "Relationship Communication Tools"
    if "parenting stress" in low or "family conflict" in low:
        return "Family Check In Worksheets"
    if "sleep help" in low or "insomnia help" in low or "sleep hygiene" in low:
        return "Sleep and Stress Reset"
    if "burnout" in low or "burnout recovery" in low or "work stress" in low:
        return "Burnout Recovery Printables"
    return "Mental Health Conversation Guides"


def build_pin_title(new_title: str) -> str:
    title = new_title.replace("| Printable Worksheet PDF", "").strip()
    return title[:100]


def build_pin_description(tags: list[str], opening: str) -> str:
    keyword_line = ", ".join(tags[:4])
    description = (
        f"{opening} Use this printable guide to start hard conversations with less panic and more clarity. "
        f"Keywords: {keyword_line}."
    )
    return description[:500]


def build_etsy_url(listing_id: int, campaign: str) -> str:
    base = f"https://www.etsy.com/listing/{listing_id}"
    query = urlencode(
        {
            "utm_source": "pinterest",
            "utm_medium": "organic",
            "utm_campaign": campaign,
        }
    )
    return f"{base}?{query}"


def load_updates() -> list[dict]:
    if not SEO_PLAN_FILE.exists():
        raise SystemExit(f"Missing file: {SEO_PLAN_FILE}")
    payload = json.loads(SEO_PLAN_FILE.read_text(encoding="utf-8"))
    return payload.get("updates", [])


def write_master_csv(rows: list[dict]):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    headers = [
        "guide_id",
        "listing_id",
        "board",
        "pin_title",
        "pin_description",
        "destination_url",
        "image_path",
    ]
    with MASTER_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def write_schedule_csv(rows: list[dict], start: date, daily_pins: int):
    schedule_rows: list[dict] = []
    current_day = start
    slot = 0
    for idx, row in enumerate(rows[: daily_pins * 14], 1):
        schedule_rows.append(
            {
                "day_index": idx,
                "publish_date": current_day.isoformat(),
                "guide_id": row["guide_id"],
                "board": row["board"],
                "pin_title": row["pin_title"],
                "destination_url": row["destination_url"],
                "image_path": row["image_path"],
            }
        )
        slot += 1
        if slot >= daily_pins:
            current_day += timedelta(days=1)
            slot = 0

    headers = [
        "day_index",
        "publish_date",
        "guide_id",
        "board",
        "pin_title",
        "destination_url",
        "image_path",
    ]
    with SCHEDULE_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(schedule_rows)


def main():
    parser = argparse.ArgumentParser(description="Generate Pinterest automation files from Etsy data")
    parser.add_argument("--campaign", default="etsy_growth_q2", help="UTM campaign name")
    parser.add_argument("--daily-pins", type=int, default=4, help="Pins per day for schedule")
    parser.add_argument("--start-date", default=date.today().isoformat(), help="Schedule start date YYYY-MM-DD")
    args = parser.parse_args()

    updates = load_updates()
    rows: list[dict] = []

    for item in updates:
        guide_id = item["guide_id"]
        listing_id = item["listing_id"]
        tags = item.get("new_tags", [])
        opening = item.get("new_description_opening", "")
        image_path = f"output/etsy/listing-images/{guide_id}/image-1.png"

        rows.append(
            {
                "guide_id": guide_id,
                "listing_id": listing_id,
                "board": board_for_tags(tags),
                "pin_title": build_pin_title(item["new_title"]),
                "pin_description": build_pin_description(tags, opening),
                "destination_url": build_etsy_url(listing_id, args.campaign),
                "image_path": image_path,
            }
        )

    rows.sort(key=lambda r: (r["board"], r["guide_id"]))
    write_master_csv(rows)

    start = date.fromisoformat(args.start_date)
    write_schedule_csv(rows, start, args.daily_pins)

    summary = {
        "total_pins": len(rows),
        "daily_pins": args.daily_pins,
        "schedule_days": 14,
        "start_date": args.start_date,
        "files": {
            "pins_master_csv": str(MASTER_CSV.relative_to(ROOT)),
            "pins_14day_schedule_csv": str(SCHEDULE_CSV.relative_to(ROOT)),
        },
        "boards": sorted({row["board"] for row in rows}),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Generated {len(rows)} Pinterest pin rows")
    print(f"  {MASTER_CSV}")
    print(f"  {SCHEDULE_CSV}")
    print(f"  {SUMMARY_JSON}")


if __name__ == "__main__":
    main()
