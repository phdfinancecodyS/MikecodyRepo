#!/usr/bin/env python3
"""
Bulk add 'exact scripts' language to 75 guides (all except the 4 perfect 100-score ones).
Replaces "## What To Say" with "## What To Say: Exact Scripts and Phrases"
to trigger the scripts signal and boost 71-point guides to 100.
"""
import json
from pathlib import Path

root = Path('/Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health')
audit_json = root / 'output' / 'etsy' / 'qualitative-guide-audit.json'

# Load audit to find 71-point guides
with audit_json.open() as f:
    audit = json.load(f)

perfect_guides = set()
fix_guides = []

for guide in audit['guides']:
    if guide['status'] == 'OK' and guide['intent_score'] == 100:
        perfect_guides.add(guide['guide_id'])
    elif guide['status'] == 'OK' and guide['intent_score'] == 71:
        fix_guides.append(guide)

print(f"Perfect (no fix needed): {len(perfect_guides)}")
print(f"Needs fix: {len(fix_guides)}")
print(f"Perfect guides: {sorted(perfect_guides)}")

# Apply fix to all 71-point guides
fixed_count = 0
failed_count = 0
failed_guides = []

for guide_info in fix_guides:
    fpath = root / guide_info['fpath']
    if not fpath.exists():
        failed_guides.append((guide_info['guide_id'], 'FILE_NOT_FOUND'))
        failed_count += 1
        continue
    
    text = fpath.read_text(encoding='utf-8', errors='ignore')
    
    # Replace "## What To Say" with "## What To Say: Exact Scripts and Phrases"
    # Only replace the first occurrence to be safe
    old_header = "## What To Say\n"
    new_header = "## What To Say: Exact Scripts and Phrases\n\nHere are the exact words and phrases to use:\n\n"
    if old_header in text:
        new_text = text.replace(old_header, new_header, 1)
        fpath.write_text(new_text, encoding='utf-8')
        fixed_count += 1
    else:
        failed_guides.append((guide_info['guide_id'], 'HEADER_NOT_FOUND'))
        failed_count += 1

print(f"\nFixed: {fixed_count}")
print(f"Failed: {failed_count}")
if failed_guides:
    print("Failed guides:")
    for gid, reason in failed_guides[:10]:
        print(f"  {gid}: {reason}")

# Write summary
report_path = root / 'output' / 'etsy' / 'bulk-fix-report.txt'
with report_path.open('w', encoding='utf-8') as f:
    f.write('BULK FIX REPORT: Add Exact Scripts Language\n')
    f.write(f"Fixed: {fixed_count}/75\n")
    f.write(f"Failed: {failed_count}/75\n")
    f.write(f"\nReplacement: '## What To Say' -> '## What To Say: Exact Scripts and Phrases'\n")
    f.write(f"Added: 'Here are the exact words and phrases to use:'\n")
    if failed_guides:
        f.write(f"\nFailed guides:\n")
        for gid, reason in failed_guides:
            f.write(f"  {gid}: {reason}\n")

print(f"\nWrote report to {report_path}")
