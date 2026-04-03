#!/usr/bin/env python3
"""
Build kit zip files for every guide x audience combination.
Each zip contains: guide markdown + 2 worksheets.

Usage:
    python3 scripts/build_kit_zips.py           # build all
    python3 scripts/build_kit_zips.py --dry-run  # preview only
"""
import os
import sys
import zipfile
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDES_DIR = ROOT / "content" / "topic-guides" / "audience-slants"
WORKSHEETS_DIR = ROOT / "content" / "worksheets"
OUTPUT_DIR = ROOT / "output" / "kits"

DRY_RUN = "--dry-run" in sys.argv


def find_guide_ids_for_audience(audience: str) -> list[str]:
    """Extract guide IDs from audience-slant directory."""
    audience_dir = GUIDES_DIR / audience
    if not audience_dir.is_dir():
        return []
    ids = []
    for f in sorted(audience_dir.glob("*.md")):
        guide_id = f.stem  # e.g. ch-01-always-on-your-high-alert-brain
        ids.append(guide_id)
    return ids


def find_worksheets(audience: str, guide_id: str) -> list[Path]:
    """Find worksheet files for a guide in the audience worksheet dir."""
    ws_dir = WORKSHEETS_DIR / audience
    if not ws_dir.is_dir():
        return []
    pattern = f"{guide_id}-worksheet-*.md"
    return sorted(ws_dir.glob(pattern))


def build_kit_zip(audience: str, guide_id: str) -> tuple[bool, str]:
    """Build a single kit zip. Returns (success, message)."""
    guide_path = GUIDES_DIR / audience / f"{guide_id}.md"
    if not guide_path.exists():
        return False, f"guide not found: {guide_path}"

    worksheets = find_worksheets(audience, guide_id)

    out_dir = OUTPUT_DIR / audience
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{guide_id}-kit.zip"

    if DRY_RUN:
        ws_count = len(worksheets)
        return True, f"[dry-run] {zip_path.relative_to(ROOT)} (guide + {ws_count} worksheets)"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(guide_path, f"{guide_id}.md")
        for ws in worksheets:
            zf.write(ws, ws.name)

    file_count = 1 + len(worksheets)
    size_kb = zip_path.stat().st_size / 1024
    return True, f"{zip_path.relative_to(ROOT)} ({file_count} files, {size_kb:.1f} KB)"


def main():
    if DRY_RUN:
        print("DRY RUN: No files will be created.\n")

    audiences = sorted(d.name for d in GUIDES_DIR.iterdir() if d.is_dir())
    total_built = 0
    total_skipped = 0
    total_missing_ws = 0

    for audience in audiences:
        guide_ids = find_guide_ids_for_audience(audience)
        print(f"\n{audience} ({len(guide_ids)} guides)")

        for guide_id in guide_ids:
            ok, msg = build_kit_zip(audience, guide_id)
            worksheets = find_worksheets(audience, guide_id)

            if ok:
                total_built += 1
                if len(worksheets) < 2:
                    total_missing_ws += 1
                    print(f"  WARN  {msg} (only {len(worksheets)} worksheets)")
                else:
                    print(f"  OK    {msg}")
            else:
                total_skipped += 1
                print(f"  SKIP  {msg}")

    print(f"\n{'='*60}")
    print(f"  Built: {total_built}  Skipped: {total_skipped}  Missing worksheets: {total_missing_ws}")
    if not DRY_RUN:
        print(f"  Output: {OUTPUT_DIR.relative_to(ROOT)}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
